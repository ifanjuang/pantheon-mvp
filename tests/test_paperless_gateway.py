from __future__ import annotations

from fastapi.testclient import TestClient

from mvp_vertical.paperless import PaperlessSourceCapture
from mvp_vertical.paperless_gateway import (
    _intake_policy_candidate,
    _load_task_contract_yaml,
    create_app,
)
from mvp_vertical.policy_gate import StandInPolicyClient


class _FakePaperless:
    def __init__(self) -> None:
        self.updates = []
        self.captures = []

    def probe(self):
        return {"reachable": True, "document_count": 2}

    def list_documents(self, *, query=None, page=1, page_size=50):
        return {
            "count": 1,
            "results": [
                {
                    "id": 42,
                    "title": "CCTP charpente",
                    "tags": [3],
                    "content": "derived OCR should not be exposed by the projection",
                    "__search_hit__": {"score": 0.9, "rank": 0, "highlights": "CCTP"},
                }
            ],
        }

    def get_document(self, document_id, *, version_id=None):
        return {
            "id": document_id,
            "title": "CCTP charpente",
            "document_type": 7,
            "content": "not part of the bounded projection",
        }

    def capture_document(self, document_id, *, version_id):
        self.captures.append((document_id, version_id))
        return PaperlessSourceCapture(
            document_id=document_id,
            version_id=version_id,
            original_filename="cctp.pdf",
            media_type="application/pdf",
            byte_size=3,
            content_hash="sha256:abc",
            storage_reference=f"paperless://document/{document_id}/version/{version_id}",
            source_ref=f"paperless/{document_id}/versions/{version_id}/cctp.pdf",
            content=b"pdf",
        )

    def get_task(self, task_id):
        return {"task_id": task_id, "status": "SUCCESS", "related_document": 42}

    def update_document_metadata(self, document_id, changes):
        self.updates.append((document_id, changes))
        return {"id": document_id, **changes}


def _decision_payload(decided_by="marie.dupont"):
    scope = {"scope_type": "project", "scope_id": "P-42"}
    return {
        "decision": {"decision_id": "d1", "decided_by": decided_by, "scope": scope},
        "expectation": {"required_scope": scope},
    }


def _contract_yaml(source_ref="paperless/42/versions/7/cctp.pdf", project_id="P-42"):
    return f"""object_type: task_contract
object_id: tc.project-42
contract_id: tc.project-42
status: active
requested_by: marie.dupont
approval_ceiling: C1
scope:
  dossier: project-42
  parent_project_id: {project_id}
  declared_sources:
    - source_ref: {source_ref}
expected_outputs:
  - Project Document Candidate
"""


def _intake_decision(fake: _FakePaperless, contract_yaml: str):
    contract = _load_task_contract_yaml(contract_yaml)
    capture = fake.capture_document(42, version_id="7")
    expected = _intake_policy_candidate(contract, capture)["decision_expectation"]
    return {
        "decision": {
            "decision_id": "decision-intake-42",
            "decided_by": "marie.dupont",
            "expires_at": "2026-07-24T12:00:00Z",
            "approval_level": expected["required_ceiling"],
            "scope": expected["required_scope"],
            "object_identity": expected["object_identity"],
            "content_digest": expected["expected_digest"],
        },
        # Deliberately wrong caller expectation: the PEP must replace it with its
        # own effect-derived expectation before decision validation.
        "expectation": {
            "required_ceiling": "C0",
            "required_scope": {"scope_type": "project", "scope_id": "ATTACKER"},
            "object_identity": "fake",
            "expected_digest": "sha256:fake",
        },
    }


def _app(fake, policy=None, intake_calls=None):
    calls = intake_calls if intake_calls is not None else []

    def intake_executor(contract, capture, ingestion_id):
        calls.append((contract.contract_id, capture.storage_reference, ingestion_id))
        return {
            "chunks_ingested": 2,
            "document": {"document_id": "doc-42", "source_ref": capture.source_ref},
            "binding": {"storage_reference": capture.storage_reference},
        }

    return create_app(
        paperless_factory=lambda: fake,
        policy_factory=lambda: policy or StandInPolicyClient(),
        intake_executor=intake_executor,
        read_api_key="read-key",
        hermes_api_key="hermes-key",
    )


def test_health_exposes_reachability_without_document_data():
    client = TestClient(_app(_FakePaperless()))
    assert client.get("/health").json() == {
        "status": "ok",
        "paperless_reachable": True,
        "write_surface": "governed_only",
        "intake_surface": "governed_only",
    }


def test_read_routes_accept_cockpit_or_hermes_key_but_not_unknown_key():
    client = TestClient(_app(_FakePaperless()))
    assert client.get("/v1/paperless/documents").status_code == 401
    for key in ("read-key", "hermes-key"):
        ok = client.get(
            "/v1/paperless/documents?query=CCTP",
            headers={"Authorization": f"Bearer {key}"},
        )
        assert ok.status_code == 200
        payload = ok.json()
        assert payload["documents"][0]["title"] == "CCTP charpente"
        assert "content" not in payload["documents"][0]
        assert payload["documents"][0]["authority"]["business_classification"] is False
    assert client.get(
        "/v1/paperless/documents", headers={"Authorization": "Bearer unknown"}
    ).status_code == 401


def test_exact_capture_returns_identity_not_bytes():
    client = TestClient(_app(_FakePaperless()))
    response = client.get(
        "/v1/paperless/documents/42/capture?version_id=7",
        headers={"Authorization": "Bearer read-key"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["storage_reference"] == "paperless://document/42/version/7"
    assert payload["source_ref"] == "paperless/42/versions/7/cctp.pdf"
    assert "content" not in payload
    assert payload["authority"]["source_capture_candidate"] is True


def test_task_success_is_explicitly_not_evidence():
    client = TestClient(_app(_FakePaperless()))
    response = client.get(
        "/v1/paperless/tasks/task-1",
        headers={"Authorization": "Bearer read-key"},
    )
    assert response.status_code == 200
    assert response.json()["runtime_success_is_evidence"] is False


def test_intake_requires_hermes_key():
    fake = _FakePaperless()
    response = TestClient(_app(fake)).post(
        "/v1/paperless/intakes",
        json={
            "paperless_document_id": 42,
            "paperless_version_id": "7",
            "task_contract_yaml": _contract_yaml(),
            "decision_payload": _decision_payload(),
        },
        headers={"Authorization": "Bearer read-key"},
    )
    assert response.status_code == 401


def test_intake_scope_is_checked_before_policy_or_database_effect():
    fake = _FakePaperless()
    policy = StandInPolicyClient()
    calls = []
    response = TestClient(_app(fake, policy, calls)).post(
        "/v1/paperless/intakes",
        json={
            "paperless_document_id": 42,
            "paperless_version_id": "7",
            "task_contract_yaml": _contract_yaml("paperless/999/versions/1/other.pdf"),
            "decision_payload": _decision_payload(),
        },
        headers={"Authorization": "Bearer hermes-key"},
    )
    assert response.status_code == 422
    assert "outside declared perimeter" in response.json()["detail"]
    assert policy.last_preflight is None
    assert calls == []


def test_intake_policy_block_prevents_database_effect():
    fake = _FakePaperless()
    calls = []
    policy = StandInPolicyClient(disposition="blocked_pending_human_decision")
    response = TestClient(_app(fake, policy, calls)).post(
        "/v1/paperless/intakes",
        json={
            "paperless_document_id": 42,
            "paperless_version_id": "7",
            "task_contract_yaml": _contract_yaml(),
            "decision_payload": _decision_payload(),
        },
        headers={"Authorization": "Bearer hermes-key"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["effect_ran"] is False
    assert calls == []
    assert policy.last_preflight["request"]["intent"] == "project_document_intake"
    assert policy.last_preflight["request"]["external_effect"] is False
    assert policy.last_preflight["gate_signals"]["task_contract_ref"] == "tc.project-42"


def test_intake_binds_decision_to_exact_capture_contract_and_scope():
    fake = _FakePaperless()
    calls = []
    policy = StandInPolicyClient()
    contract_yaml = _contract_yaml()
    decision = _intake_decision(fake, contract_yaml)
    fake.captures.clear()

    response = TestClient(_app(fake, policy, calls)).post(
        "/v1/paperless/intakes",
        json={
            "paperless_document_id": 42,
            "paperless_version_id": "7",
            "task_contract_yaml": contract_yaml,
            "decision_payload": decision,
            "ingestion_id": "hermes-intake-1",
        },
        headers={"Authorization": "Bearer hermes-key"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "applied"
    assert payload["effect_ran"] is True
    assert payload["operation"] == "project_document_intake"
    assert payload["source_ref"] == "paperless/42/versions/7/cctp.pdf"
    assert payload["knowledge_published"] is False
    assert payload["evidence_admitted"] is False
    assert calls == [
        ("tc.project-42", "paperless://document/42/version/7", "hermes-intake-1")
    ]
    expected = payload["decision_expectation"]
    assert expected["required_scope"] == {"scope_type": "project", "scope_id": "P-42"}
    assert expected["required_ceiling"] == "C1"
    assert expected["object_identity"] == "paperless-intake:tc.project-42:42:7"
    assert expected["expected_digest"].startswith("sha256:")
    assert policy.last_decision["expectation"] == expected
    assert policy.last_decision["expectation"] != decision["expectation"]


def test_intake_wrong_human_object_identity_is_blocked_after_pep_binding():
    fake = _FakePaperless()
    calls = []
    policy = StandInPolicyClient()
    contract_yaml = _contract_yaml()
    decision = _intake_decision(fake, contract_yaml)
    decision["decision"]["object_identity"] = "paperless-intake:tc.project-42:42:WRONG"
    fake.captures.clear()

    response = TestClient(_app(fake, policy, calls)).post(
        "/v1/paperless/intakes",
        json={
            "paperless_document_id": 42,
            "paperless_version_id": "7",
            "task_contract_yaml": contract_yaml,
            "decision_payload": decision,
        },
        headers={"Authorization": "Bearer hermes-key"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert response.json()["effect_ran"] is False
    assert calls == []
    assert any("object_identity" in item for item in response.json()["reasons"])


def test_metadata_write_requires_hermes_key():
    client = TestClient(_app(_FakePaperless()))
    response = client.post(
        "/v1/paperless/documents/42/metadata",
        json={"changes": {"tags": [3]}, "decision_payload": _decision_payload()},
        headers={"Authorization": "Bearer read-key"},
    )
    assert response.status_code == 401


def test_metadata_write_is_blocked_before_paperless_when_policy_blocks():
    fake = _FakePaperless()
    client = TestClient(
        _app(fake, StandInPolicyClient(disposition="blocked_pending_human_decision"))
    )
    response = client.post(
        "/v1/paperless/documents/42/metadata",
        json={"changes": {"tags": [3]}, "decision_payload": _decision_payload()},
        headers={"Authorization": "Bearer hermes-key"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "blocked"
    assert fake.updates == []


def test_metadata_write_applies_after_policy_and_human_decision():
    fake = _FakePaperless()
    client = TestClient(_app(fake))
    response = client.post(
        "/v1/paperless/documents/42/metadata",
        json={
            "changes": {"tags": [3, 8]},
            "decision_payload": _decision_payload(),
            "candidate": {"classification_status": "candidate_reviewed"},
        },
        headers={"Authorization": "Bearer hermes-key"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    assert fake.updates == [(42, {"tags": [3, 8]})]
