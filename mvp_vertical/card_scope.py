"""Server-side resolution of explicitly requested Cockpit Card descendants.

DOM nesting is not treated as a security boundary. This resolver expands only
relations declared by the current Cockpit model and only when the caller asks
for that expansion explicitly.
"""

from __future__ import annotations

from typing import Any

import psycopg

from . import agency_data, agency_directory, store


class CardScopeError(ValueError):
    pass


def _strip_prefix(value: str, prefix: str) -> str:
    return value[len(prefix):] if value.startswith(prefix) else value


def resolve_declared_descendants(
    conn: psycopg.Connection,
    *,
    root_entity: dict[str, Any],
) -> dict:
    entity_id = str(root_entity.get("entity_id") or "").strip()
    entity_type = str(root_entity.get("entity_type") or "").strip()
    if not entity_id or not entity_type:
        raise CardScopeError("root entity requires stable entity_id and entity_type")

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

    # Other card families currently have no server-declared descendant expansion.
    # They remain root-only unless the user explicitly adds Context Resolver items.
    return {
        "policy": "root_only",
        "root_owner_id": entity_id,
        "descendants": [],
        "source_refs": [],
        "counts": {},
    }
