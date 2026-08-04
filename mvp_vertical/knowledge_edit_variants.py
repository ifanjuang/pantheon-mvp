"""Immutable proposal variants for one bounded Knowledge edit request.

A variant shares the request's exact Knowledge version, selection range and
selection digest. Selecting a variant is a human review event, not an edit.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from . import knowledge


MIGRATION = Path(__file__).resolve().parent / "sql" / "009_knowledge_edit_variants.sql"
VARIANT_LABELS = ("A", "B")
REVIEWABLE_STATUSES = {
    "queued_for_hermes",
    "proposed",
    "applied",
    "conflict",
    "rejected",
}


class KnowledgeEditVariantError(knowledge.KnowledgeError):
    pass


class KnowledgeEditVariantConflict(knowledge.StaleKnowledgeWrite):
    pass


def ensure_schema(conn: psycopg.Connection) -> None:
    conn.execute(MIGRATION.read_text(encoding="utf-8"))
    conn.commit()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _payload_digest(value: dict[str, Any]) -> str:
    canonical = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return _digest(canonical)


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _knowledge_snapshot(
    conn: psycopg.Connection,
    knowledge_id: str,
    *,
    lock: bool = False,
) -> dict:
    suffix = " FOR UPDATE" if lock else ""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT knowledge_id, version, markdown, markdown_digest FROM knowledge_items "
            f"WHERE knowledge_id = %s{suffix}",
            (knowledge_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise knowledge.KnowledgeNotFound(f"unknown Knowledge item: {knowledge_id}")
    return dict(row)


def _request_row(
    conn: psycopg.Connection,
    request_id: str,
    *,
    lock: bool = False,
) -> dict:
    suffix = " FOR UPDATE" if lock else ""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT * FROM knowledge_edit_requests WHERE request_id = %s{suffix}",
            (request_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise knowledge.KnowledgeNotFound(f"unknown intelligent edit request: {request_id}")
    return dict(row)


def _variant_row(conn: psycopg.Connection, variant_id: str) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM knowledge_edit_variants WHERE variant_id = %s",
            (variant_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise knowledge.KnowledgeNotFound(f"unknown intelligent edit variant: {variant_id}")
    return dict(row)


def _variants(conn: psycopg.Connection, request_id: str) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM knowledge_edit_variants WHERE request_id = %s "
            "ORDER BY variant_label, created_at, variant_id",
            (request_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def _events(conn: psycopg.Connection, request_id: str) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM knowledge_edit_review_events WHERE request_id = %s "
            "ORDER BY occurred_at, event_id",
            (request_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def _event_by_key(conn: psycopg.Connection, idempotency_key: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM knowledge_edit_review_events WHERE idempotency_key = %s",
            (idempotency_key,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def _insert_event(
    conn: psycopg.Connection,
    *,
    request_id: str,
    event_type: str,
    actor: str,
    actor_kind: str,
    idempotency_key: str,
    payload: dict[str, Any],
) -> None:
    pdigest = _payload_digest(payload)
    conn.execute(
        """
        INSERT INTO knowledge_edit_review_events (
            event_id, request_id, event_type, actor, actor_kind,
            idempotency_key, payload_digest, payload
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            f"edit-review-event-{uuid.uuid4().hex}",
            request_id,
            event_type,
            actor,
            actor_kind,
            idempotency_key,
            pdigest,
            Jsonb(payload),
        ),
    )


def _selection_diff(selected_text: str, replacement: str, label: str) -> str:
    return "".join(
        difflib.unified_diff(
            selected_text.splitlines(keepends=True),
            replacement.splitlines(keepends=True),
            fromfile="selection",
            tofile=f"variant-{label}",
        )
    )


def _validate_scope(request: dict, item: dict) -> str:
    start = request["selection_start"]
    end = request["selection_end"]
    if item["version"] != request["base_version"]:
        return "stale_version"
    if start < 0 or end < start or end > len(item["markdown"]):
        return "invalid_range"
    selected = item["markdown"][start:end]
    if _digest(selected) != request["selected_text_digest"]:
        return "stale_selection"
    return "current"


def get_variant_review(conn: psycopg.Connection, request_id: str) -> dict:
    request = _request_row(conn, request_id)
    item = _knowledge_snapshot(conn, request["knowledge_id"])
    selected_text = request.get("selected_text_snapshot")
    if selected_text is None and _validate_scope(request, item) == "current":
        selected_text = item["markdown"][request["selection_start"]:request["selection_end"]]
    selected_text = selected_text or ""

    variants = _variants(conn, request_id)
    if not variants and request.get("replacement_markdown"):
        variants = [
            {
                "variant_id": f"single:{request_id}",
                "request_id": request_id,
                "variant_label": "A",
                "replacement_markdown": request["replacement_markdown"],
                "replacement_digest": _digest(request["replacement_markdown"]),
                "proposed_by": "legacy_proposal",
                "created_at": request["updated_at"],
            }
        ]

    projected_variants = []
    for variant in variants:
        projected = _jsonable(dict(variant))
        projected["diff"] = _selection_diff(
            selected_text,
            str(variant["replacement_markdown"]),
            str(variant["variant_label"]),
        )
        projected["selected"] = variant["variant_id"] == request.get("selected_variant_id")
        projected_variants.append(projected)

    request_projection = _jsonable(request)
    request_projection["selected_text"] = selected_text
    request_projection["scope_status"] = _validate_scope(request, item)
    request_projection["variant_count"] = len(projected_variants)
    return {
        "edit_request": request_projection,
        "variants": projected_variants,
        "review_events": _jsonable(_events(conn, request_id)),
        "knowledge": {
            "knowledge_id": item["knowledge_id"],
            "version": item["version"],
            "markdown_digest": item["markdown_digest"],
        },
        "variant_selected_is_edit_applied": False,
        "proposal_is_evidence": False,
    }


def list_variant_reviews(
    conn: psycopg.Connection,
    *,
    knowledge_id: str,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    if status is not None and status not in REVIEWABLE_STATUSES:
        raise KnowledgeEditVariantError("unsupported intelligent edit review status")
    if limit < 1 or limit > 100:
        raise KnowledgeEditVariantError("review list limit must be between 1 and 100")
    parameters: list[Any] = [knowledge_id]
    clause = ""
    if status is not None:
        clause = " AND status = %s"
        parameters.append(status)
    parameters.append(limit)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT request_id FROM knowledge_edit_requests "
            f"WHERE knowledge_id = %s{clause} ORDER BY created_at DESC, request_id LIMIT %s",
            tuple(parameters),
        )
        ids = [row[0] for row in cur.fetchall()]
    return [get_variant_review(conn, request_id) for request_id in ids]


def create_variant_request(
    conn: psycopg.Connection,
    *,
    request_id: str,
    knowledge_id: str,
    instruction_kind: str,
    instruction: str,
    base_version: int,
    selection_start: int,
    selection_end: int,
    selected_text: str,
    requested_by: str,
    requested_variant_count: int,
    idempotency_key: str,
) -> dict:
    if instruction_kind not in knowledge.INSTRUCTION_KINDS or not instruction.strip():
        raise KnowledgeEditVariantError("invalid or empty intelligent-edit instruction")
    if requested_variant_count not in (1, 2):
        raise KnowledgeEditVariantError("requested_variant_count must be 1 or 2")
    if not request_id.strip() or not requested_by.strip() or len(idempotency_key.strip()) < 8:
        raise KnowledgeEditVariantError("request identity, human actor and idempotency key are required")

    payload = {
        "request_id": request_id,
        "knowledge_id": knowledge_id,
        "instruction_kind": instruction_kind,
        "instruction": instruction,
        "base_version": base_version,
        "selection_start": selection_start,
        "selection_end": selection_end,
        "selected_text": selected_text,
        "requested_by": requested_by,
        "requested_variant_count": requested_variant_count,
    }
    pdigest = _payload_digest(payload)
    with conn.transaction():
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT request_id, request_payload_digest FROM knowledge_edit_requests "
                "WHERE request_idempotency_key = %s",
                (idempotency_key,),
            )
            replay = cur.fetchone()
        if replay is not None:
            if replay["request_payload_digest"] != pdigest:
                raise knowledge.IdempotencyConflict(
                    "edit request idempotency key has different content"
                )
            return get_variant_review(conn, replay["request_id"])

        item = _knowledge_snapshot(conn, knowledge_id, lock=True)
        if item["version"] != base_version:
            raise knowledge.StaleKnowledgeWrite(
                f"offline edit is based on version {base_version}; current version is {item['version']}"
            )
        if selection_start < 0 or selection_end < selection_start or selection_end > len(item["markdown"]):
            raise KnowledgeEditVariantError("selection range is outside the Markdown snapshot")
        if item["markdown"][selection_start:selection_end] != selected_text:
            raise knowledge.StaleKnowledgeWrite(
                "selected text no longer matches the declared base snapshot"
            )

        conn.execute(
            """
            INSERT INTO knowledge_edit_requests (
                request_id, knowledge_id, instruction_kind, instruction, base_version,
                selection_start, selection_end, selected_text_digest,
                selected_text_snapshot, requested_variant_count,
                replacement_markdown, status, requested_by,
                request_idempotency_key, request_payload_digest
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL,
                      'queued_for_hermes', %s, %s, %s)
            """,
            (
                request_id,
                knowledge_id,
                instruction_kind,
                instruction,
                base_version,
                selection_start,
                selection_end,
                _digest(selected_text),
                selected_text,
                requested_variant_count,
                requested_by,
                idempotency_key,
                pdigest,
            ),
        )
    return get_variant_review(conn, request_id)


def submit_variant(
    conn: psycopg.Connection,
    *,
    request_id: str,
    variant_label: str,
    replacement_markdown: str,
    proposed_by: str,
    idempotency_key: str,
) -> dict:
    label = variant_label.strip().upper()
    replacement = replacement_markdown.strip()
    if label not in VARIANT_LABELS or not replacement or not proposed_by.strip():
        raise KnowledgeEditVariantError("variant label, replacement Markdown and proposer are required")
    payload = {
        "request_id": request_id,
        "variant_label": label,
        "replacement_markdown": replacement,
        "proposed_by": proposed_by,
    }
    pdigest = _payload_digest(payload)

    with conn.transaction():
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT request_id, payload_digest FROM knowledge_edit_variants "
                "WHERE idempotency_key = %s",
                (idempotency_key,),
            )
            replay = cur.fetchone()
        if replay is not None:
            if replay["request_id"] != request_id or replay["payload_digest"] != pdigest:
                raise knowledge.IdempotencyConflict(
                    "variant idempotency key belongs to another immutable proposal"
                )
            return get_variant_review(conn, request_id)

        request = _request_row(conn, request_id, lock=True)
        if request["status"] not in {"queued_for_hermes", "proposed"}:
            raise KnowledgeEditVariantConflict(
                f"proposal variant cannot be submitted from status {request['status']}"
            )
        if request["requested_variant_count"] == 1 and label != "A":
            raise KnowledgeEditVariantError("single-variant requests accept label A only")
        item = _knowledge_snapshot(conn, request["knowledge_id"], lock=True)
        if _validate_scope(request, item) != "current":
            conn.execute(
                "UPDATE knowledge_edit_requests SET status = 'conflict', "
                "updated_at = CURRENT_TIMESTAMP WHERE request_id = %s",
                (request_id,),
            )
            raise KnowledgeEditVariantConflict(
                "Knowledge changed before the proposal variant was submitted"
            )

        variant_id = f"edit-variant-{uuid.uuid4().hex}"
        try:
            conn.execute(
                """
                INSERT INTO knowledge_edit_variants (
                    variant_id, request_id, variant_label, replacement_markdown,
                    replacement_digest, proposed_by, idempotency_key, payload_digest
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    variant_id,
                    request_id,
                    label,
                    replacement,
                    _digest(replacement),
                    proposed_by,
                    idempotency_key,
                    pdigest,
                ),
            )
        except psycopg.errors.UniqueViolation as exc:
            raise knowledge.IdempotencyConflict(
                f"variant {label} already exists for this edit request"
            ) from exc
        _insert_event(
            conn,
            request_id=request_id,
            event_type="variant_proposed",
            actor=proposed_by,
            actor_kind="hermes",
            idempotency_key=idempotency_key,
            payload={
                "variant_id": variant_id,
                "variant_label": label,
                "replacement_digest": _digest(replacement),
                "base_version": request["base_version"],
                "selected_text_digest": request["selected_text_digest"],
                "project_mutated": False,
                "evidence_admitted": False,
            },
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM knowledge_edit_variants WHERE request_id = %s",
                (request_id,),
            )
            count = cur.fetchone()[0]
        if count >= request["requested_variant_count"]:
            conn.execute(
                "UPDATE knowledge_edit_requests SET status = 'proposed', "
                "replacement_markdown = CASE WHEN requested_variant_count = 1 "
                "THEN %s ELSE replacement_markdown END, updated_at = CURRENT_TIMESTAMP "
                "WHERE request_id = %s",
                (replacement if request["requested_variant_count"] == 1 else None, request_id),
            )
    return get_variant_review(conn, request_id)


def select_variant(
    conn: psycopg.Connection,
    *,
    request_id: str,
    variant_id: str,
    actor: str,
    idempotency_key: str,
) -> dict:
    payload = {"request_id": request_id, "variant_id": variant_id, "actor": actor}
    pdigest = _payload_digest(payload)
    replay = _event_by_key(conn, idempotency_key)
    if replay is not None:
        if replay["request_id"] != request_id or replay["payload_digest"] != pdigest:
            raise knowledge.IdempotencyConflict(
                "variant selection idempotency key belongs to another review event"
            )
        return get_variant_review(conn, request_id)

    with conn.transaction():
        request = _request_row(conn, request_id, lock=True)
        if request["status"] != "proposed":
            raise KnowledgeEditVariantConflict(
                f"variant cannot be selected from status {request['status']}"
            )
        variant = _variant_row(conn, variant_id)
        if variant["request_id"] != request_id:
            raise KnowledgeEditVariantError("variant does not belong to this edit request")
        conn.execute(
            "UPDATE knowledge_edit_requests SET selected_variant_id = %s, selected_by = %s, "
            "selected_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
            "WHERE request_id = %s",
            (variant_id, actor, request_id),
        )
        _insert_event(
            conn,
            request_id=request_id,
            event_type="variant_selected",
            actor=actor,
            actor_kind="human",
            idempotency_key=idempotency_key,
            payload={
                "variant_id": variant_id,
                "variant_label": variant["variant_label"],
                "replacement_digest": variant["replacement_digest"],
                "edit_applied": False,
                "knowledge_mutated": False,
                "evidence_admitted": False,
            },
        )
    return get_variant_review(conn, request_id)


def reject_request(
    conn: psycopg.Connection,
    *,
    request_id: str,
    actor: str,
    reason: str,
    idempotency_key: str,
) -> dict:
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise KnowledgeEditVariantError("rejection reason is required")
    payload = {"request_id": request_id, "actor": actor, "reason": normalized_reason}
    pdigest = _payload_digest(payload)
    replay = _event_by_key(conn, idempotency_key)
    if replay is not None:
        if replay["request_id"] != request_id or replay["payload_digest"] != pdigest:
            raise knowledge.IdempotencyConflict(
                "rejection idempotency key belongs to another review event"
            )
        return get_variant_review(conn, request_id)

    with conn.transaction():
        request = _request_row(conn, request_id, lock=True)
        if request["status"] not in {"queued_for_hermes", "proposed"}:
            raise KnowledgeEditVariantConflict(
                f"edit request cannot be rejected from status {request['status']}"
            )
        conn.execute(
            "UPDATE knowledge_edit_requests SET status = 'rejected', "
            "updated_at = CURRENT_TIMESTAMP WHERE request_id = %s",
            (request_id,),
        )
        _insert_event(
            conn,
            request_id=request_id,
            event_type="request_rejected",
            actor=actor,
            actor_kind="human",
            idempotency_key=idempotency_key,
            payload={
                "reason": normalized_reason,
                "knowledge_mutated": False,
                "task_authorized": False,
                "evidence_admitted": False,
            },
        )
    return get_variant_review(conn, request_id)


def apply_selected_variant(
    conn: psycopg.Connection,
    *,
    request_id: str,
    actor: str,
    idempotency_key: str,
) -> dict:
    request = _request_row(conn, request_id)
    if request["status"] == "applied":
        applied = knowledge.apply_edit_request(
            conn,
            request_id=request_id,
            actor=actor,
            actor_kind="human",
            idempotency_key=idempotency_key,
        )
        return {**applied, "review": get_variant_review(conn, request_id)}
    if request["status"] != "proposed":
        raise KnowledgeEditVariantConflict(
            f"selected variant cannot be applied from status {request['status']}"
        )
    if not request.get("selected_variant_id"):
        raise KnowledgeEditVariantError("select one proposal variant before applying it")
    variant = _variant_row(conn, request["selected_variant_id"])
    if variant["request_id"] != request_id:
        raise KnowledgeEditVariantError("selected variant does not belong to this request")

    with conn.transaction():
        locked = _request_row(conn, request_id, lock=True)
        if locked["status"] != "proposed" or locked["selected_variant_id"] != variant["variant_id"]:
            raise KnowledgeEditVariantConflict("edit request changed before application")
        conn.execute(
            "UPDATE knowledge_edit_requests SET replacement_markdown = %s, "
            "updated_at = CURRENT_TIMESTAMP WHERE request_id = %s",
            (variant["replacement_markdown"], request_id),
        )

    applied = knowledge.apply_edit_request(
        conn,
        request_id=request_id,
        actor=actor,
        actor_kind="human",
        idempotency_key=idempotency_key,
    )
    event_payload = {
        "variant_id": variant["variant_id"],
        "variant_label": variant["variant_label"],
        "replacement_digest": variant["replacement_digest"],
        "applied_version": applied["knowledge"]["version"],
        "review_status_promoted": False,
        "evidence_admitted": False,
    }
    with conn.transaction():
        existing = _event_by_key(conn, idempotency_key)
        if existing is None:
            _insert_event(
                conn,
                request_id=request_id,
                event_type="variant_applied",
                actor=actor,
                actor_kind="human",
                idempotency_key=idempotency_key,
                payload=event_payload,
            )
    return {**applied, "review": get_variant_review(conn, request_id)}
