"""API checks for normalized Hermes runtime return callbacks."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mvp_vertical import hermes_runtime_return
from mvp_vertical.cockpit_shell import create_cockpit_app


class _Connection:
    def close(self) -> None:
        pass


def _client() -> TestClient:
    return TestClient(
        create_cockpit_app(
            connect_fn=_Connection,
            api_key="read-key",
            editor_api_key="editor-key",
            hermes_api_key="hermes-key",
        )
    )


def test_only_hermes_can_report_normalized_return(monkeypatch) -> None:
    observed = {}

    def record(_conn, **values):
        observed.update(values)
        return {
            "admission_id": values["admission_id"],
            "run_id": values["run_id"],
            "runtime_return_recorded": True,
            "runtime_status": "returned",
            "work_issue": {"status": "review"},
            "result_status": "candidate",
            "evidence_admitted": False,
            "issue_closed": False,
        }

    monkeypatch.setattr(hermes_runtime_return, "record_external_runtime_return", record)
    client = _client()
    body = {
        "normalized_return": {
            "outcome": "result_candidate",
            "summary": "Résultat à relire",
            "trace_refs": ["hermes://trace/123"],
            "result_refs": [],
            "evidence_candidate_refs": [],
        },
        "expected_issue_version": 2,
        "idempotency_key": "runtime-return-123",
    }

    denied = client.post(
        "/v1/hermes/execution-admissions/admission-1/runs/run-1/return",
        headers={
            "Authorization": "Bearer editor-key",
            "X-Pantheon-Hermes-Actor": "hermes-adapter",
        },
        json=body,
    )
    assert denied.status_code == 401

    accepted = client.post(
        "/v1/hermes/execution-admissions/admission-1/runs/run-1/return",
        headers={
            "Authorization": "Bearer hermes-key",
            "X-Pantheon-Hermes-Actor": "hermes-adapter",
        },
        json=body,
    )
    assert accepted.status_code == 200
    payload = accepted.json()
    assert payload["result_status"] == "candidate"
    assert payload["evidence_admitted"] is False
    assert payload["issue_closed"] is False
    assert observed["admission_id"] == "admission-1"
    assert observed["run_id"] == "run-1"
    assert observed["normalized_return"] == body["normalized_return"]


def test_return_shape_requires_summary_and_trace_refs() -> None:
    client = _client()
    response = client.post(
        "/v1/hermes/execution-admissions/admission-1/runs/run-1/return",
        headers={
            "Authorization": "Bearer hermes-key",
            "X-Pantheon-Hermes-Actor": "hermes-adapter",
        },
        json={
            "normalized_return": {"outcome": "result_candidate"},
            "expected_issue_version": 2,
            "idempotency_key": "runtime-return-invalid",
        },
    )
    assert response.status_code == 422


def test_return_shape_rejects_unimplemented_rich_fields() -> None:
    client = _client()
    response = client.post(
        "/v1/hermes/execution-admissions/admission-1/runs/run-1/return",
        headers={
            "Authorization": "Bearer hermes-key",
            "X-Pantheon-Hermes-Actor": "hermes-adapter",
        },
        json={
            "normalized_return": {
                "outcome": "result_candidate",
                "summary": "Résultat à relire",
                "trace_refs": ["hermes://trace/123"],
                "source_refs": ["nas://project/source.pdf"],
            },
            "expected_issue_version": 2,
            "idempotency_key": "runtime-return-rich",
        },
    )
    assert response.status_code == 422
