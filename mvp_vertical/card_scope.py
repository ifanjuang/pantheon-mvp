"""Server-side resolution of explicitly requested Cockpit Card scope.

DOM nesting is not treated as a security boundary. This resolver expands only
relations declared by the current Cockpit model and only when the caller asks
for that expansion explicitly.
"""

from __future__ import annotations

from typing import Any

import psycopg

from . import agency_data, agency_directory, knowledge, store, work_issues


class CardScopeError(ValueError):
    pass


def _strip_prefix(value: str, prefix: str) -> str:
    return value[len(prefix):] if value.startswith(prefix) else value


def _root_identity(root_entity: dict[str, Any]) -> tuple[str, str]:
    entity_id = str(root_entity.get("entity_id") or "").strip()
    entity_type = str(root_entity.get("entity_type") or "").strip()
    if not entity_id or not entity_type:
        raise CardScopeError("root entity requires stable entity_id and entity_type")
    return entity_id, entity_type


def resolve_declared_descendants(
    conn: psycopg.Connection,
    *,
    root_entity: dict[str, Any],
) -> dict:
    entity_id, entity_type = _root_identity(root_entity)

    if entity_type == "project":
        project_id = _strip_prefix(entity_id, "project:")
        try:
            agency_data.get_project(conn, project_id)
        except agency_data.ProjectNotFound as exc:
            raise CardScopeError(str(exc)) from exc

        participations = agency_directory.list_project_participations(conn, project_id)
        documents = store.list_document_cards(conn, project_id)
        descendants = [
            {
                "entity_id": f"participation:{item['participation_id']}",
                "entity_type": "project_participation",
            }
            for item in participations
        ]
        descendants.extend(
            {
                "entity_id": f"document:{item['document_id']}",
                "entity_type": "document",
            }
            for item in documents
        )
        return {
            "policy": "project_declared_children",
            "root_owner_id": project_id,
            "descendants": descendants,
            "source_refs": [item["source_ref"] for item in documents if item.get("source_ref")],
            "counts": {
                "project_participations": len(participations),
                "documents": len(documents),
            },
        }

    if entity_type == "document":
        document_id = _strip_prefix(entity_id, "document:")
        try:
            document = store.get_document_card_by_id(conn, document_id)
        except KeyError as exc:
            raise CardScopeError(str(exc)) from exc
        return {
            "policy": "document_source_only",
            "root_owner_id": document_id,
            "descendants": [],
            "source_refs": [document["source_ref"]] if document.get("source_ref") else [],
            "counts": {"documents": 1},
        }

    return {
        "policy": "root_only",
        "root_owner_id": entity_id,
        "descendants": [],
        "source_refs": [],
        "counts": {},
    }


def resolve_case_ref(
    conn: psycopg.Connection,
    *,
    root_entity: dict[str, Any],
) -> str:
    """Resolve the owning project/case before an internal Work Issue is created."""
    entity_id, entity_type = _root_identity(root_entity)

    if entity_type == "project":
        project_id = _strip_prefix(entity_id, "project:")
        try:
            agency_data.get_project(conn, project_id)
        except agency_data.ProjectNotFound as exc:
            raise CardScopeError(str(exc)) from exc
        return project_id

    if entity_type == "document":
        document_id = _strip_prefix(entity_id, "document:")
        try:
            return str(store.get_document_card_by_id(conn, document_id)["parent_project_id"])
        except KeyError as exc:
            raise CardScopeError(str(exc)) from exc

    if entity_type == "knowledge":
        knowledge_id = _strip_prefix(entity_id, "knowledge:")
        try:
            return str(knowledge.get_knowledge_card(conn, knowledge_id)["parent_project_id"])
        except knowledge.KnowledgeNotFound as exc:
            raise CardScopeError(str(exc)) from exc

    if entity_type == "work_issue":
        issue_id = _strip_prefix(entity_id, "work:")
        try:
            return str(work_issues.get_issue(conn, issue_id)["case_ref"])
        except work_issues.WorkIssueNotFound as exc:
            raise CardScopeError(str(exc)) from exc

    if entity_type == "project_participation":
        participation_id = _strip_prefix(entity_id, "participation:")
        row = conn.execute(
            "SELECT project_id FROM agency_project_participations WHERE participation_id = %s",
            (participation_id,),
        ).fetchone()
        if row is None:
            raise CardScopeError(f"unknown Agency ProjectParticipation: {participation_id}")
        return str(row[0])

    raise CardScopeError(
        f"Hermes handoff submission requires a project-scoped root; unsupported root type: {entity_type}"
    )
