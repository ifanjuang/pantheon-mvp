"""Acceptance tests for read-only resolved Category collections."""

from __future__ import annotations

import psycopg
import pytest

from mvp_vertical import (
    agency_classification,
    agency_data,
    category_collection_read,
    cockpit_composed,
    information_projection,
    project_documents,
    store,
    work_issues,
)


@pytest.fixture
def conn():
    try:
        connection = store.connect()
    except Exception as exc:  # pragma: no cover - local unit-only environment
        pytest.skip(f"PostgreSQL unreachable: {exc}")
    connection.execute(work_issues.MIGRATION.read_text(encoding="utf-8"))
    connection.execute(agency_data.MIGRATION.read_text(encoding="utf-8"))
    connection.execute(project_documents.MIGRATION.read_text(encoding="utf-8"))
    connection.execute(information_projection.MIGRATION.read_text(encoding="utf-8"))
    connection.execute(agency_classification.MIGRATION.read_text(encoding="utf-8"))
    connection.execute(
        """
        TRUNCATE agency_category_assignments, agency_categories,
                 agency_information_projection_events,
                 agency_information_document_links,
                 agency_information_projection_metadata,
                 knowledge_items, extraction_runs, document_versions, source_documents,
                 doc_document_events, doc_document_versions, doc_documents,
                 issue_events, hermes_runs, issue_comments, work_card_metadata, work_issues,
                 agency_information_cards, agency_people, agency_organizations, agency_projects
        RESTART IDENTITY CASCADE
        """
    )
    connection.commit()
    yield connection
    connection.close()


def _project(conn, project_id: str = "project-category-read") -> str:
    conn.execute(
        """
        INSERT INTO agency_projects (
            project_id, code, display_name, created_by, updated_by
        ) VALUES (%s, %s, %s, 'human:test', 'human:test')
        """,
        (project_id, project_id.upper(), "Projet Category Read"),
    )
    conn.commit()
    return project_id


def _information(conn, project_id: str, information_id: str = "information-category-read") -> str:
    conn.execute(
        """
        INSERT INTO agency_information_cards (
            information_id, series_id, project_id, title, category,
            source_type, source_note, index_label, status
        ) VALUES (%s, %s, %s, 'Information', 'legacy', 'draft',
                  'Source', 'A01', 'draft')
        """,
        (information_id, f"series-{information_id}", project_id),
    )
    conn.commit()
    return information_id


def _document(conn, project_id: str, document_id: str = "document-category-read") -> str:
    conn.execute(
        """
        INSERT INTO doc_documents (
            document_id, parent_project_id, document_type, title, created_by
        ) VALUES (%s, %s, 'regulation', 'PLUi Métropole', 'human:test')
        """,
        (document_id, project_id),
    )
    conn.commit()
    return document_id


def _knowledge(conn, project_id: str, knowledge_id: str = "knowledge-category-read") -> str:
    source_id = f"source-{knowledge_id}"
    extraction_id = f"extraction-{knowledge_id}"
    conn.execute(
        """
        INSERT INTO source_documents (
            document_id, dossier, parent_project_id, source_ref, source_digest,
            media_type, byte_size, analysis_status
        ) VALUES (%s, %s, %s, %s, %s, 'text/plain', 20, 'extracted')
        """,
        (source_id, project_id, project_id, f"nas://{source_id}", f"digest-{source_id}"),
    )
    conn.execute(
        """
        INSERT INTO extraction_runs (
            extraction_id, document_id, contract_id, contract_digest, source_digest,
            converter, converter_version, config_digest, status
        ) VALUES (%s, %s, 'contract-test', 'contract-digest', %s,
                  'fixture', '1', 'config-digest', 'complete')
        """,
        (extraction_id, source_id, f"digest-{source_id}"),
    )
    conn.execute(
        """
        INSERT INTO knowledge_items (
            knowledge_id, document_id, source_version, source_digest, extraction_id,
            title, family, markdown, markdown_digest, source_chunk_refs,
            review_status, version, created_by
        ) VALUES (%s, %s, 1, %s, %s, 'Règles PLUi', 'reglementations',
                  '# Règles', 'markdown-digest', '[]'::jsonb,
                  'reviewed', 1, 'human:test')
        """,
        (knowledge_id, source_id, f"digest-{source_id}", extraction_id),
    )
    conn.commit()
    return knowledge_id


def _work_issue(conn, issue_id: str = "work-category-read") -> str:
    conn.execute(
        """
        INSERT INTO work_issues (
            issue_id, case_ref, title, description, origin, issue_type,
            priority, requested_effect, status, created_by
        ) VALUES (%s, 'case-category-read', 'Vérifier', 'Vérification',
                  'human', 'verification', 'normal', 'read_only', 'open', 'human:test')
        """,
        (issue_id,),
    )
    conn.commit()
    return issue_id


def _category(
    conn,
    category_id: str,
    *,
    parent_category_id: str | None = None,
    applies_to: list[str] | None = None,
) -> None:
    agency_classification.create_category(
        conn,
        category_id=category_id,
        title=category_id.replace("-", " ").title(),
        parent_category_id=parent_category_id,
        applies_to=applies_to or ["document"],
        actor="human:test",
    )


def test_resolved_collection_composes_existing_owner_reads_without_changing_identity(conn) -> None:
    project_id = _project(conn)
    information_id = _information(conn, project_id)
    document_id = _document(conn, project_id)
    knowledge_id = _knowledge(conn, project_id)
    issue_id = _work_issue(conn)
    endpoints = {
        "project": project_id,
        "information": information_id,
        "document": document_id,
        "knowledge": knowledge_id,
        "work_issue": issue_id,
    }

    _category(conn, "reglementations", applies_to=list(endpoints))
    _category(
        conn,
        "urbanisme",
        parent_category_id="reglementations",
        applies_to=["document", "knowledge"],
    )
    for entity_type, entity_id in endpoints.items():
        agency_classification.assign_category(
            conn,
            assignment_id=f"assignment-{entity_type}",
            category_id="reglementations",
            entity_type=entity_type,
            entity_id=entity_id,
            actor="human:test",
        )

    projection = category_collection_read.get_resolved_category_collection(
        conn,
        "reglementations",
    )

    assert projection["collection_is_projection_input"] is True
    assert projection["classification_is_not_authorization"] is True
    assert projection["authorization_inferred"] is False
    assert projection["collection"]["collection_id"] == "children:category:reglementations"
    assert projection["collection"]["parent_entity_id"] == "category:reglementations"
    assert projection["collection"]["state"] == "loaded"
    assert [
        category["category_id"] for category in projection["collection"]["child_categories"]
    ] == ["urbanisme"]

    members = {
        item["entity_ref"]["entity_type"]: item
        for item in projection["collection"]["members"]
    }
    assert set(members) == set(endpoints)
    assert members["project"]["read_model"]["project_id"] == project_id
    assert members["information"]["read_model"]["information"]["information_id"] == information_id
    assert members["document"]["read_model"]["document_id"] == document_id
    assert members["knowledge"]["read_model"]["knowledge_id"] == knowledge_id
    assert members["work_issue"]["read_model"]["issue_id"] == issue_id
    for entity_type, entity_id in endpoints.items():
        member = members[entity_type]
        assert member["entity_ref"] == {"entity_type": entity_type, "entity_id": entity_id}
        assert member["assignment"]["category_id"] == "reglementations"


def test_same_owner_identity_resolves_in_multiple_category_collections_without_duplication(conn) -> None:
    project_id = _project(conn, "project-multi-category")
    document_id = _document(conn, project_id, "document:plui-metropole")
    _category(conn, "urbanisme")
    _category(conn, "referentiels")

    for category_id in ("urbanisme", "referentiels"):
        agency_classification.assign_category(
            conn,
            assignment_id=f"assignment:{category_id}",
            category_id=category_id,
            entity_type="document",
            entity_id=document_id,
            actor="human:test",
        )

    first = category_collection_read.get_resolved_category_collection(conn, "urbanisme")
    second = category_collection_read.get_resolved_category_collection(conn, "referentiels")
    first_member = first["collection"]["members"][0]
    second_member = second["collection"]["members"][0]

    assert first_member["entity_ref"] == second_member["entity_ref"] == {
        "entity_type": "document",
        "entity_id": document_id,
    }
    assert first_member["read_model"]["document_id"] == document_id
    assert second_member["read_model"]["document_id"] == document_id
    assert conn.execute(
        "SELECT count(*) FROM doc_documents WHERE document_id = %s",
        (document_id,),
    ).fetchone()[0] == 1


def test_empty_category_projects_an_explicit_empty_collection(conn) -> None:
    _category(conn, "empty-category")
    projection = category_collection_read.get_resolved_category_collection(
        conn,
        "empty-category",
    )
    assert projection["collection"]["state"] == "empty"
    assert projection["collection"]["child_categories"] == []
    assert projection["collection"]["members"] == []


def test_resolved_category_collection_route_is_mounted_in_composed_cockpit() -> None:
    app = cockpit_composed.create_composed_cockpit_app(
        connect_fn=lambda: None,
        initialize_fn=None,
        api_key="read-secret",
        editor_api_key="editor-secret",
        hermes_api_key="hermes-secret",
    )
    methods_by_path: dict[str, set[str]] = {}
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            methods_by_path.setdefault(route.path, set()).update(route.methods or set())

    assert "GET" in methods_by_path[
        "/agency/categories/{category_id}/resolved-collection"
    ]
