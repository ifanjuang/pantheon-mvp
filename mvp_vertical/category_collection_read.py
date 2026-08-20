"""Read-only owner resolution for persisted Category collection inputs.

Category and CategoryAssignment remain owned by ``agency_classification``. This
adapter only composes existing bounded owner reads so the Cockpit can fetch one
heterogeneous Category collection without becoming an entity-type router.
It creates no Card record, changes no owner, infers no authorization and does
not qualify Evidence.
"""

from __future__ import annotations

from typing import Any, Callable

import psycopg

from . import (
    agency_classification,
    agency_data,
    information_projection,
    knowledge,
    project_documents,
    work_issue_read,
    work_issues,
)


class CategoryCollectionReadError(ValueError):
    """Base refusal for Category collection read composition."""


class CategoryCollectionIntegrityError(CategoryCollectionReadError):
    """An active CategoryAssignment no longer resolves to its declared owner."""


OwnerReader = Callable[[psycopg.Connection, str], dict[str, Any]]


def _information_read(conn: psycopg.Connection, information_id: str) -> dict[str, Any]:
    return information_projection.get_projection(conn, information_id)


def _work_issue_read(conn: psycopg.Connection, issue_id: str) -> dict[str, Any]:
    return work_issue_read.get_issue_record(conn, issue_id)


_OWNER_READERS: dict[str, OwnerReader] = {
    "project": agency_data.get_project,
    "information": _information_read,
    "document": project_documents.get_document,
    "knowledge": knowledge.get_knowledge_card,
    "work_issue": _work_issue_read,
}

_OWNER_NOT_FOUND = (
    agency_data.ProjectNotFound,
    information_projection.InformationProjectionNotFound,
    project_documents.ProjectDocumentNotFound,
    knowledge.KnowledgeNotFound,
    work_issues.IssueNotFound,
)


def _resolve_assignment(
    conn: psycopg.Connection,
    assignment: dict[str, Any],
) -> dict[str, Any]:
    entity_type = str(assignment.get("entity_type") or "").strip()
    entity_id = str(assignment.get("entity_id") or "").strip()
    reader = _OWNER_READERS.get(entity_type)
    if reader is None:
        raise CategoryCollectionReadError(
            f"unsupported CategoryAssignment entity type: {entity_type or '<empty>'}"
        )
    if not entity_id:
        raise CategoryCollectionReadError("CategoryAssignment entity_id is required")
    try:
        read_model = reader(conn, entity_id)
    except _OWNER_NOT_FOUND as exc:
        raise CategoryCollectionIntegrityError(
            f"active CategoryAssignment references missing owner: {entity_type}:{entity_id}"
        ) from exc
    return {
        "entity_ref": {"entity_type": entity_type, "entity_id": entity_id},
        "assignment": assignment,
        "read_model": read_model,
    }


def get_resolved_category_collection(
    conn: psycopg.Connection,
    category_id: str,
) -> dict[str, Any]:
    """Resolve one Category Collection through existing owner read boundaries.

    Child Categories remain Category records. Directly assigned entities are
    resolved through their existing owner read adapters and retain the exact
    CategoryAssignment that caused them to appear here.
    """

    source = agency_classification.get_category_collection(conn, category_id)
    child_categories = list(source["child_categories"])
    members = [
        _resolve_assignment(conn, assignment)
        for assignment in source["assignments"]
    ]
    state = "loaded" if child_categories or members else "empty"
    return {
        "category": source["category"],
        "collection": {
            "collection_id": f"children:category:{category_id}",
            "parent_entity_id": f"category:{category_id}",
            "state": state,
            "child_categories": child_categories,
            "members": members,
        },
        "collection_is_projection_input": True,
        "classification_is_not_authorization": True,
        "authorization_inferred": False,
    }
