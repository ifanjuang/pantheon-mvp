"""Tests for preview-only Cockpit -> Hermes handoff candidates."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mvp_vertical import hermes_handoff_preview
from mvp_vertical.cockpit_shell import create_cockpit_app


class _Connection:
    def close(self) -> None:
        pass


def test_handoff_preview_is_deterministic_read_only_and_not_authorized() -> None:
    request = {
        "question": "Quels points structurels dois-je vérifier ?",
        "card_context_envelope": {
            "root_entity": {"entity_id": "project:lieurey", "entity_type": "project"},
            "descendants": [
                {"entity_id": "document:cctp", "entity_type": "document"},
            ],
            "source_refs": ["source:cctp.pdf", "source:cctp.pdf"],
            "explicit_additions": [],
            "explicit_exclusions": [],
            "scope_widened_implicitly": False,
        },
        "selected_context": [
            {"entity_id": "person:bet", "entity_type": "person"},
        ],
    }
    first = hermes_handoff_preview.build_preview(**request)
    second = hermes_handoff_preview.build_preview(**request)

    assert first == second
    assert first["requested_effect"] == "read_only"
    assert first["execution_authorized"] is False
    assert first["task_contract"]["task_contract_ref"].startswith("task-contract-candidate:")
    assert first["context_pack"]["context_pack_ref"].startswith("context-pack-candidate:")
    assert first["context_pack"]["scope_widened_implicitly"] is False
    assert len(first["context_pack"]["source_refs"]) == 1
    assert first["task_contract"]["forbidden_outputs"] == [
        "external_effect",
        "canonical_effect",
        "memory_promotion",
        "agency_data_mutation",
    ]


def test_handoff_preview_exclusions_win_over_selected_context() -> None:
    preview = hermes_handoff_preview.build_preview(
        question="Résume le dossier",
        card_context_envelope={
            "root_entity": {"entity_id": "project:lieurey", "entity_type": "project"},
            "descendants": [],
            "source_refs": [],
            "explicit_additions": [],
            "explicit_exclusions": [
                {"entity_id": "person:private", "entity_type": "person"},
            ],
        },
        selected_context=[
            {"entity_id": "person:private", "entity_type": "person"},
            {"entity_id": "org:bet", "entity_type": "organization"},
        ],
    )
    included = preview["context_pack"]["included_entities"]
    assert {"entity_id": "person:private", "entity_type": "person"} not in included
    assert {"entity_id": "org:bet", "entity_type": "organization"} in included


def test_handoff_preview_api_requires_read_key_and_refuses_implicit_scope_widening() -> None:
    client = TestClient(
        create_cockpit_app(
            connect_fn=_Connection,
            api_key="read-key",
        )
    )
    body = {
        "question": "Que faut-il examiner ?",
        "card_context_envelope": {
            "root_entity": {"entity_id": "project:lieurey", "entity_type": "project"},
            "descendants": [],
            "source_refs": [],
            "explicit_additions": [],
            "explicit_exclusions": [],
            "scope_widened_implicitly": False,
        },
        "selected_context": [],
    }

    denied = client.post("/v1/cockpit/hermes-handoffs/preview", json=body)
    assert denied.status_code == 401

    accepted = client.post(
        "/v1/cockpit/hermes-handoffs/preview",
        headers={"Authorization": "Bearer read-key"},
        json=body,
    )
    assert accepted.status_code == 200
    assert accepted.json()["execution_authorized"] is False

    body["card_context_envelope"]["scope_widened_implicitly"] = True
    widened = client.post(
        "/v1/cockpit/hermes-handoffs/preview",
        headers={"Authorization": "Bearer read-key"},
        json=body,
    )
    assert widened.status_code == 422
    assert "may not widen scope implicitly" in widened.json()["detail"]
