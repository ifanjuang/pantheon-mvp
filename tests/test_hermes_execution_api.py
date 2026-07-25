"""API boundary tests for execution admission and external Hermes callbacks."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mvp_vertical import hermes_execution
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


def test_human_can_admit_exact_handoff_without_starting_runtime(monkeypatch) -> None:
    observed = {}

    def admit_handoff(_conn, **values):
        observed.update(values)
        return {
            "admission_id": "admission-1",
            "handoff_id": values["handoff_id"],
            "decision": "allow",
            "requested_effect": "read_only",
            "ready_for_external_runtime": True,
            "runtime_started": False,
            "consumed_by_run_id": None,
        }

    monkeypatch.setattr(hermes_execution, "admit_handoff", admit_handoff)
    response = _client().post(
        "/v1/cockpit/hermes-handoffs/handoff-1/admissions",
        headers={
            "Authorization": "Bearer editor-key",
            "X-Pantheon-Human-Actor": "ifan",
        },
        json={"idempotency_key": "execution-admit-001"},
    )
    assert response.status_code == 201
    assert response.json()["runtime_started"] is False
    assert observed == {
        "handoff_id": "handoff-1",
        "actor": "ifan",
        "idempotency_key": "execution-admit-001",
    }


def test_execution_envelope_is_hermes_only_and_lookup_requires_admission_id(monkeypatch) -> None:
    monkeypatch.setattr(
        hermes_execution,
        "get_execution_envelope",
        lambda _conn, admission_id: {
            "kind": "hermes_execution_envelope",
            "admission": {"admission_id": admission_id},
            "dispatch_requested": False,
        },
    )
    client = _client()

    denied = client.get(
        "/v1/hermes/execution-admissions/admission-1",
        headers={"Authorization": "Bearer editor-key"},
    )
    assert denied.status_code == 401

    accepted = client.get(
        "/v1/hermes/execution-admissions/admission-1",
        headers={"Authorization": "Bearer hermes-key"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["dispatch_requested"] is False

    assert client.get(
        "/v1/hermes/execution-admissions",
        headers={"Authorization": "Bearer hermes-key"},
    ).status_code == 404


def test_only_external_hermes_can_report_runtime_start(monkeypatch) -> None:
    observed = {}

    def record_external_runtime_start(_conn, **values):
        observed.update(values)
        return {
            "admission_id": values["admission_id"],
            "run_id": values["run_id"],
            "runtime_start_recorded": True,
            "replayed": False,
            "work_issue": {"status": "in_progress"},
        }

    monkeypatch.setattr(
        hermes_execution,
        "record_external_runtime_start",
        record_external_runtime_start,
    )
    client = _client()
    body = {
        "run_id": "hermes-runtime-123",
        "expected_issue_version": 1,
        "idempotency_key": "runtime-start-123",
    }

    cockpit_denied = client.post(
        "/v1/hermes/execution-admissions/admission-1/runs/start",
        headers={
            "Authorization": "Bearer editor-key",
            "X-Pantheon-Hermes-Actor": "hermes-adapter",
        },
        json=body,
    )
    assert cockpit_denied.status_code == 401

    actor_missing = client.post(
        "/v1/hermes/execution-admissions/admission-1/runs/start",
        headers={"Authorization": "Bearer hermes-key"},
        json=body,
    )
    assert actor_missing.status_code == 422

    started = client.post(
        "/v1/hermes/execution-admissions/admission-1/runs/start",
        headers={
            "Authorization": "Bearer hermes-key",
            "X-Pantheon-Hermes-Actor": "hermes-adapter",
        },
        json=body,
    )
    assert started.status_code == 201
    assert observed["run_id"] == "hermes-runtime-123"
    assert observed["actor"] == "hermes-adapter"
    assert observed["expected_issue_version"] == 1
