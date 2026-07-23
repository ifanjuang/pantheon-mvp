from __future__ import annotations

import json

import httpx

from mvp_vertical.policy_gate import HttpPolicyClient, governed_effect
from mvp_vertical.policy_request import build_preflight_payload


def _decision_payload():
    scope = {"scope_type": "project", "scope_id": "P-42"}
    return {
        "decision": {
            "decision_id": "decision-42",
            "decided_by": "marie.dupont",
            "expires_at": "2026-07-24T12:00:00Z",
            "approval_level": "C1",
            "scope": scope,
            "object_identity": "paperless:42:7",
            "content_digest": "sha256:abc",
        },
        "expectation": {
            "required_ceiling": "C1",
            "required_scope": scope,
            "object_identity": "paperless:42:7",
            "expected_digest": "sha256:abc",
        },
    }


def test_flat_runtime_candidate_is_translated_to_policy_http_contract():
    payload = build_preflight_payload(
        {
            "effect_kind": "external_document_metadata_update",
            "resource": "paperless_ngx",
            "document_id": 42,
            "changed_fields": ["tags"],
        },
        _decision_payload(),
    )

    assert set(payload) == {"request", "gate_signals"}
    assert payload["request"] == {
        "intent": "external_document_metadata_update",
        "external_effect": True,
        "writes_state": True,
        "transmission_requested": False,
        "memory_promotion_requested": False,
        "professional_position": False,
        "financial_or_contractual_effect": False,
        "scope": {"scope_type": "project", "scope_id": "P-42"},
    }
    assert payload["gate_signals"] == {
        "human_decision_ref": "decision-42",
        "human_decision_level": "C1",
    }
    assert "effect_kind" not in payload
    assert "document_id" not in payload


def test_explicit_task_contract_signal_is_preserved():
    payload = build_preflight_payload(
        {
            "request": {
                "intent": "project_document_intake",
                "external_effect": False,
                "writes_state": True,
                "scope": {"scope_type": "project", "scope_id": "P-42"},
            },
            "gate_signals": {"task_contract_ref": "tc.project-42"},
        },
        _decision_payload(),
    )
    assert payload["request"]["external_effect"] is False
    assert payload["gate_signals"] == {
        "task_contract_ref": "tc.project-42",
        "human_decision_ref": "decision-42",
        "human_decision_level": "C1",
    }


def test_http_policy_client_receives_only_contract_fields_and_effect_runs_after_valid_verdict():
    observed = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        observed.append((request.url.path, body, request.headers.get("authorization")))
        if request.url.path.endswith("preflights:evaluate"):
            assert set(body) == {"request", "gate_signals"}
            return httpx.Response(
                200,
                json={
                    "policy_disposition": "eligible_with_gate_signals_unverified",
                    "missing_requirements": [],
                },
            )
        if request.url.path.endswith("decisions:validate"):
            return httpx.Response(200, json={"verdict": "valid", "findings": []})
        return httpx.Response(404)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    policy = HttpPolicyClient("http://pantheon-policy-api:8000", "policy-key", client=http)
    ran = []
    result = governed_effect(
        policy,
        candidate={
            "effect_kind": "external_document_metadata_update",
            "resource": "paperless_ngx",
        },
        decision_payload=_decision_payload(),
        effect=lambda: ran.append("applied") or {"ok": True},
    )

    assert result["status"] == "applied"
    assert result["effect_ran"] is True
    assert ran == ["applied"]
    assert observed[0][0] == "/v1/policy/preflights:evaluate"
    assert observed[0][2] == "Bearer policy-key"
    assert observed[1][0] == "/v1/policy/decisions:validate"
