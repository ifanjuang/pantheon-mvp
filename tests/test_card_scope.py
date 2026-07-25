"""Unit tests for server-side declared Card descendant resolution."""

from __future__ import annotations

from mvp_vertical import agency_data, agency_directory, card_scope, store


class _Connection:
    pass


def test_project_scope_resolves_only_participations_and_direct_documents(monkeypatch) -> None:
    monkeypatch.setattr(
        agency_data,
        "get_project",
        lambda _conn, project_id: {"project_id": project_id},
    )
    monkeypatch.setattr(
        agency_directory,
        "list_project_participations",
        lambda _conn, project_id: [
            {"participation_id": "bet", "project_id": project_id},
            {"participation_id": "client", "project_id": project_id},
        ],
    )
    monkeypatch.setattr(
        store,
        "list_document_cards",
        lambda _conn, project_id: [
            {"document_id": "cctp", "source_ref": f"nas://{project_id}/cctp.pdf"},
        ],
    )

    resolved = card_scope.resolve_declared_descendants(
        _Connection(),
        root_entity={"entity_id": "project:lieurey", "entity_type": "project"},
    )

    assert resolved["policy"] == "project_declared_children"
    assert resolved["descendants"] == [
        {"entity_id": "participation:bet", "entity_type": "project_participation"},
        {"entity_id": "participation:client", "entity_type": "project_participation"},
        {"entity_id": "document:cctp", "entity_type": "document"},
    ]
    assert resolved["source_refs"] == ["nas://lieurey/cctp.pdf"]
    assert resolved["counts"] == {"project_participations": 2, "documents": 1}


def test_document_scope_adds_source_but_no_implicit_relations(monkeypatch) -> None:
    monkeypatch.setattr(
        store,
        "get_document_card_by_id",
        lambda _conn, document_id: {
            "document_id": document_id,
            "source_ref": "nas://lieurey/cctp.pdf",
        },
    )
    resolved = card_scope.resolve_declared_descendants(
        _Connection(),
        root_entity={"entity_id": "document:cctp", "entity_type": "document"},
    )
    assert resolved["policy"] == "document_source_only"
    assert resolved["descendants"] == []
    assert resolved["source_refs"] == ["nas://lieurey/cctp.pdf"]


def test_unknown_card_family_stays_root_only() -> None:
    resolved = card_scope.resolve_declared_descendants(
        _Connection(),
        root_entity={"entity_id": "space:outils", "entity_type": "cockpit_space"},
    )
    assert resolved == {
        "policy": "root_only",
        "root_owner_id": "space:outils",
        "descendants": [],
        "source_refs": [],
        "counts": {},
    }
