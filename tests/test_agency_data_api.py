"""HTTP boundary tests for the PostgreSQL Agency Data surface."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mvp_vertical import agency_data
from mvp_vertical.cockpit_shell import create_cockpit_app


class _Connection:
    def close(self) -> None:
        pass


def test_agency_project_list_accepts_cockpit_and_hermes_read_keys(monkeypatch) -> None:
    observed = []

    def list_projects(_conn, *, query, limit):
        observed.append((query, limit))
        return [{"project_id": "project-lieurey", "code": "LIEUREY", "revision": 4}]

    monkeypatch.setattr(agency_data, "list_projects", list_projects)
    client = TestClient(
        create_cockpit_app(
            connect_fn=_Connection,
            api_key="read-key",
            hermes_api_key="hermes-key",
        )
    )

    cockpit = client.get(
        "/v1/agency/projects",
        params={"q": "lie", "limit": 20},
        headers={"Authorization": "Bearer read-key"},
    )
    assert cockpit.status_code == 200
    assert cockpit.json()["system_of_record"] == "postgres"

    hermes = client.get(
        "/v1/agency/projects",
        headers={"Authorization": "Bearer hermes-key"},
    )
    assert hermes.status_code == 200
    assert observed == [("lie", 20), (None, 100)]


def test_hermes_reversible_project_update_is_bounded_and_does_not_infer_approval(monkeypatch) -> None:
    observed = {}

    def update_project(_conn, **values):
        observed.update(values)
        return {
            "project_id": values["project_id"],
            "description": values["changes"]["description"],
            "revision": values["expected_revision"] + 1,
            "owner_system": "postgres",
        }

    monkeypatch.setattr(agency_data, "update_project", update_project)
    client = TestClient(
        create_cockpit_app(
            connect_fn=_Connection,
            editor_api_key="editor-key",
            hermes_api_key="hermes-key",
        )
    )

    response = client.patch(
        "/v1/agency/projects/project-lieurey",
        headers={
            "Authorization": "Bearer hermes-key",
            "X-Pantheon-Actor": "hermes-agency-adapter",
        },
        json={
            "expected_revision": 4,
            "idempotency_key": "idem-hermes-0001",
            "description": "Description de travail enrichie.",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["effect"] == "internal_agency_data_write"
    assert payload["approval_inferred"] is False
    assert observed["actor_kind"] == "hermes"
    assert observed["actor"] == "hermes-agency-adapter"
    assert observed["changes"] == {"description": "Description de travail enrichie."}
    assert observed["expected_revision"] == 4


def test_hermes_consequential_field_surfaces_missing_governance_gate(monkeypatch) -> None:
    def update_project(_conn, **_values):
        raise agency_data.GovernanceGateRequired("Hermes Agency Data mutation requires a verifiable Pantheon gate for field(s): phase")

    monkeypatch.setattr(agency_data, "update_project", update_project)
    client = TestClient(
        create_cockpit_app(
            connect_fn=_Connection,
            editor_api_key="editor-key",
            hermes_api_key="hermes-key",
        )
    )
    response = client.patch(
        "/v1/agency/projects/project-lieurey",
        headers={
            "Authorization": "Bearer hermes-key",
            "X-Pantheon-Actor": "hermes-agency-adapter",
        },
        json={
            "expected_revision": 4,
            "idempotency_key": "idem-hermes-phase",
            "phase": "DCE",
        },
    )
    assert response.status_code == 409
    assert "verifiable Pantheon gate" in response.json()["detail"]


def test_editor_project_create_is_recorded_as_human_actor(monkeypatch) -> None:
    observed = {}

    def create_project(_conn, **values):
        observed.update(values)
        return {"project_id": values["project_id"], "revision": 1, "owner_system": "postgres"}

    monkeypatch.setattr(agency_data, "create_project", create_project)
    client = TestClient(
        create_cockpit_app(
            connect_fn=_Connection,
            editor_api_key="editor-key",
            hermes_api_key="hermes-key",
        )
    )
    response = client.post(
        "/v1/agency/projects",
        headers={
            "Authorization": "Bearer editor-key",
            "X-Pantheon-Actor": "ifan",
        },
        json={
            "project_id": "project-lieurey",
            "code": "LIEUREY",
            "display_name": "Lieurey",
            "idempotency_key": "idem-human-0001",
        },
    )
    assert response.status_code == 201
    assert observed["actor_kind"] == "human"
    assert observed["actor"] == "ifan"


def test_agency_write_requires_actor_and_writer_key() -> None:
    client = TestClient(
        create_cockpit_app(
            connect_fn=_Connection,
            editor_api_key="editor-key",
            hermes_api_key="hermes-key",
        )
    )
    body = {
        "expected_revision": 1,
        "idempotency_key": "idem-missing-actor",
        "description": "Description bornée",
    }
    missing_actor = client.patch(
        "/v1/agency/projects/project-lieurey",
        headers={"Authorization": "Bearer hermes-key"},
        json=body,
    )
    assert missing_actor.status_code == 422

    invalid_key = client.patch(
        "/v1/agency/projects/project-lieurey",
        headers={
            "Authorization": "Bearer wrong-key",
            "X-Pantheon-Actor": "hermes-agency-adapter",
        },
        json=body,
    )
    assert invalid_key.status_code == 401


def test_same_editor_and_hermes_key_is_refused_as_ambiguous() -> None:
    client = TestClient(
        create_cockpit_app(
            connect_fn=_Connection,
            editor_api_key="shared-key",
            hermes_api_key="shared-key",
        )
    )
    response = client.patch(
        "/v1/agency/projects/project-lieurey",
        headers={
            "Authorization": "Bearer shared-key",
            "X-Pantheon-Actor": "ambiguous-actor",
        },
        json={
            "expected_revision": 1,
            "idempotency_key": "idem-ambiguous-key",
            "description": "Description bornée",
        },
    )
    assert response.status_code == 503
