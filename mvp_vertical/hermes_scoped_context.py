"""Admission-bound read-only context access for a running Hermes execution.

This module is intentionally not a general Agency Data API. It exposes only the
stable entity identities already admitted in one immutable Context Pack and only
to the exact Hermes run that consumed that admission.

The Context Pack authorizes identity/scope, not a frozen business-data snapshot.
Each entity read therefore re-reads the current owner record and reports that
freshness explicitly. Source references are provenance identifiers only in this
slice; they cannot be dereferenced here.

Returned Agency fields are frozen by explicit named schema projections. Project
and Information use their respective `hermes_context` views; adding future owner
columns therefore cannot silently widen what Hermes can read.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row

from . import (
    agency_data,
    agency_directory,
    agency_information,
    agency_schema,
    knowledge,
    store,
    work_issue_read,
    work_issues,
)

MAX_RICH_TEXT_CHARS = 500_000
FIELD_PROJECTION_VERSION = "scoped-context-v1"
MATERIALIZABLE_TYPES = {
    "project",
    "person",
    "organization",
    "information",
    "document",
    "knowledge",
    "work_issue",
}

PERSON_FIELDS = (
    "person_id",
    "display_name",
    "email",
    "phone",
    "address",
    "owner_system",
    "revision",
    "updated_at",
)
ORGANIZATION_FIELDS = (
    "organization_id",
    "name",
    "email",
    "phone",
    "address",
    "siret",
    "owner_system",
    "revision",
    "updated_at",
)
DOCUMENT_FIELDS = (
    "card_type",
    "card_id",
    "document_id",
    "parent_project_id",
    "title",
    "source_ref",
    "source_digest",
    "media_type",
    "byte_size",
    "analysis_status",
    "naming",
    "extraction",
    "authority",
)
KNOWLEDGE_FIELDS = (
    "card_type",
    "card_id",
    "knowledge_id",
    "document_ref",
    "parent_project_id",
    "title",
    "family",
    "markdown_digest",
    "source_chunk_refs",
    "review_status",
    "version",
    "created_by",
    "created_at",
    "updated_at",
    "authority",
)
WORK_ISSUE_FIELDS = (
    "issue_id",
    "case_ref",
    "title",
    "description",
    "origin",
    "parent_issue_ref",
    "primary_card_ref",
    "issue_type",
    "priority",
    "assigned_to",
    "requested_effect",
    "status",
    "close_reason",
    "task_contract_ref",
    "context_pack_ref",
    "version",
    "created_by",
    "created_at",
    "updated_at",
)


class HermesScopedContextError(ValueError):
    pass


class ScopedContextNotFound(HermesScopedContextError):
    pass


class ScopedContextConflict(HermesScopedContextError):
    pass


class ScopedContextContentTooLarge(HermesScopedContextError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strip_prefix(value: str, *prefixes: str) -> str:
    for prefix in prefixes:
        if value.startswith(prefix):
            return value[len(prefix):]
    return value


def _bounded_projection(record: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    """Project only reviewed v1 fields; schema growth cannot widen runtime access."""
    return {field: record.get(field) for field in fields if field in record}


def _runtime_scope(
    conn: psycopg.Connection,
    *,
    admission_id: str,
    run_id: str,
) -> dict[str, Any]:
    """Resolve one exact running run and its immutable admitted Context Pack."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT a.admission_id,
                   a.handoff_id,
                   a.work_issue_id,
                   a.requested_effect,
                   a.task_contract_ref AS admission_task_contract_ref,
                   a.context_pack_ref AS admission_context_pack_ref,
                   h.requested_effect AS handoff_requested_effect,
                   h.task_contract,
                   h.context_pack,
                   h.preview_digest AS handoff_preview_digest,
                   a.preview_digest AS admission_preview_digest,
                   r.run_id,
                   r.status AS run_status,
                   r.requested_effect AS run_requested_effect,
                   r.task_contract_ref AS run_task_contract_ref,
                   r.context_pack_ref AS run_context_pack_ref
              FROM hermes_execution_admissions a
              JOIN cockpit_hermes_handoffs h ON h.handoff_id = a.handoff_id
              JOIN hermes_runs r ON r.admission_ref = a.admission_id
             WHERE a.admission_id = %s
               AND r.run_id = %s
            """,
            (admission_id, run_id),
        )
        row = cur.fetchone()
    if row is None:
        raise ScopedContextNotFound(
            "no Hermes run matches this execution admission and run_id"
        )

    scope = dict(row)
    if not (
        scope["requested_effect"]
        == scope["handoff_requested_effect"]
        == scope["run_requested_effect"]
        == "read_only"
    ):
        raise ScopedContextConflict(
            "Scoped Hermes Data Access first slice requires read_only effect consistency"
        )
    if scope["run_status"] != "running":
        raise ScopedContextConflict(
            f"Scoped Hermes Data Access requires a running Hermes run; current status is {scope['run_status']}"
        )

    context_pack = dict(scope.get("context_pack") or {})
    task_contract = dict(scope.get("task_contract") or {})
    context_ref = str(context_pack.get("context_pack_ref") or "")
    task_ref = str(task_contract.get("task_contract_ref") or "")
    if not context_ref or not task_ref:
        raise ScopedContextConflict("stored handoff is missing its Task Contract or Context Pack identity")
    if not (
        context_ref == scope["admission_context_pack_ref"] == scope["run_context_pack_ref"]
        and task_ref == scope["admission_task_contract_ref"] == scope["run_task_contract_ref"]
        and scope["handoff_preview_digest"] == scope["admission_preview_digest"]
    ):
        raise ScopedContextConflict(
            "running Hermes context no longer matches the immutable admitted handoff"
        )

    scope["context_pack"] = context_pack
    scope["task_contract"] = task_contract
    return scope


def _entity_refs(context_pack: dict[str, Any]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw in context_pack.get("included_entities") or []:
        if not isinstance(raw, dict):
            raise ScopedContextConflict("stored Context Pack contains an invalid entity reference")
        entity_id = str(raw.get("entity_id") or "").strip()
        entity_type = str(raw.get("entity_type") or "").strip()
        if not entity_id or not entity_type:
            raise ScopedContextConflict("stored Context Pack contains an incomplete entity reference")
        key = (entity_type, entity_id)
        if key in seen:
            continue
        seen.add(key)
        output.append({"entity_id": entity_id, "entity_type": entity_type})
    if not output:
        raise ScopedContextConflict("stored Context Pack contains no admitted entity")
    return output


def _admitted_entity(
    context_pack: dict[str, Any],
    *,
    entity_type: str,
    entity_id: str,
) -> dict[str, str]:
    wanted = (entity_type.strip(), entity_id.strip())
    for ref in _entity_refs(context_pack):
        if (ref["entity_type"], ref["entity_id"]) == wanted:
            return ref
    raise ScopedContextConflict(
        "requested entity is outside the exact admitted Context Pack"
    )


def _bounded_text(value: str, *, label: str) -> str:
    if len(value) > MAX_RICH_TEXT_CHARS:
        raise ScopedContextContentTooLarge(
            f"{label} exceeds the first-slice limit of {MAX_RICH_TEXT_CHARS} characters"
        )
    return value


def _materialize_entity(
    conn: psycopg.Connection,
    *,
    entity_type: str,
    entity_id: str,
) -> dict[str, Any]:
    if entity_type == "project":
        raw = agency_data.get_project(conn, _strip_prefix(entity_id, "project:"))
        return {
            "record": agency_schema.project_record_for_view(raw, "hermes_context"),
            "representation": None,
            "record_owner_system": "postgres",
        }

    if entity_type == "person":
        raw = agency_directory.get_person(conn, _strip_prefix(entity_id, "person:"))
        return {
            "record": _bounded_projection(raw, PERSON_FIELDS),
            "representation": None,
            "record_owner_system": "postgres",
        }

    if entity_type == "organization":
        raw = agency_directory.get_organization(
            conn,
            _strip_prefix(entity_id, "organization:", "org:"),
        )
        return {
            "record": _bounded_projection(raw, ORGANIZATION_FIELDS),
            "representation": None,
            "record_owner_system": "postgres",
        }

    if entity_type == "information":
        information_id = _strip_prefix(entity_id, "information:")
        raw = agency_information.get_information_context(conn, information_id)["current"]
        record = agency_schema.information_record_for_view(raw, "hermes_context")
        details = _bounded_text(str(raw.get("details") or ""), label="Information details")
        source_note = _bounded_text(str(raw.get("source_note") or ""), label="Information source note")
        return {
            "record": record,
            "representation": {
                "kind": "agency_information_text",
                "summary": str(raw.get("summary") or ""),
                "details": details,
                "source_note": source_note,
                "working_assumptions_are_not_acted": raw.get("status") in {"draft", "in_progress"},
            },
            "record_owner_system": "postgres_agency_information",
        }

    if entity_type == "document":
        document_id = _strip_prefix(entity_id, "document:")
        raw = store.get_document_card_by_id(conn, document_id)
        record = _bounded_projection(raw, DOCUMENT_FIELDS)
        try:
            markdown = _bounded_text(
                store.get_document_markdown(conn, document_id),
                label="document derived Markdown",
            )
            representation: dict[str, Any] | None = {
                "kind": "derived_markdown",
                "content": markdown,
                "source_binary_included": False,
            }
        except KeyError:
            representation = None
        return {
            "record": record,
            "representation": representation,
            "record_owner_system": "postgres_document_projection",
        }

    if entity_type == "knowledge":
        knowledge_id = _strip_prefix(entity_id, "knowledge:")
        raw = knowledge.get_knowledge_card(conn, knowledge_id)
        record = _bounded_projection(raw, KNOWLEDGE_FIELDS)
        markdown = _bounded_text(
            knowledge.get_knowledge_markdown(conn, knowledge_id),
            label="Knowledge Markdown",
        )
        return {
            "record": record,
            "representation": {
                "kind": "knowledge_markdown",
                "content": markdown,
            },
            "record_owner_system": "postgres_knowledge",
        }

    if entity_type == "work_issue":
        issue_id = _strip_prefix(entity_id, "work:", "work_issue:")
        projection = work_issue_read.get_issue_projection(conn, issue_id)
        raw = projection.get("work_issue") or projection
        return {
            "record": _bounded_projection(raw, WORK_ISSUE_FIELDS),
            "representation": None,
            "record_owner_system": "postgres_work_issue",
        }

    raise ScopedContextConflict(f"unsupported admitted entity type: {entity_type}")


def get_scoped_entity(
    conn: psycopg.Connection,
    *,
    admission_id: str,
    run_id: str,
    entity_type: str,
    entity_id: str,
) -> dict[str, Any]:
    """Return one freshly re-read owner record inside one admitted running scope."""
    scope = _runtime_scope(conn, admission_id=admission_id, run_id=run_id)
    ref = _admitted_entity(
        scope["context_pack"],
        entity_type=entity_type,
        entity_id=entity_id,
    )
    materialized = _materialize_entity(
        conn,
        entity_type=ref["entity_type"],
        entity_id=ref["entity_id"],
    )
    record = materialized["record"]
    return {
        "admission_id": scope["admission_id"],
        "run_id": scope["run_id"],
        "requested_effect": scope["requested_effect"],
        "entity_type": ref["entity_type"],
        "entity_id": ref["entity_id"],
        "record": record,
        "representation": materialized["representation"],
        "record_owner_system": materialized["record_owner_system"],
        "current_revision": record.get("revision") or record.get("version"),
        "read_semantics": "current_owner_reread_within_admitted_identity_scope",
        "observed_at": _now(),
        "field_projection_version": FIELD_PROJECTION_VERSION,
        "source_refs_are_provenance_only": True,
        "global_search_available": False,
        "implicit_related_object_expansion": False,
        "write_available": False,
    }
