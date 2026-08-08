"""A6 provenance and projection for external issuer document references.

The semantic field projected by this module is ``issuer_document_reference`` on
one exact professional Project Document revision. The reference remains opaque
external vocabulary. Recording or resolving it does not order revisions, change
currentness, admit Evidence or establish professional authority.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from . import project_documents


MIGRATION = Path(__file__).resolve().parent / "sql" / "028_project_document_issuer_reference_observations.sql"
BASIS_KINDS = {"human_declared", "source_observed", "import_metadata"}
AUTHORITY = {
    "is_evidence": False,
    "is_decision": False,
    "is_approval": False,
    "is_professional_validation": False,
    "changes_revision_order": False,
    "changes_current_authority": False,
    "changes_project_truth": False,
}


class ProjectDocumentReferenceError(ValueError):
    pass


class ReferenceObservationNotFound(ProjectDocumentReferenceError):
    pass


class ReferenceIdempotencyConflict(ProjectDocumentReferenceError):
    pass


class GovernanceGateRequired(ProjectDocumentReferenceError):
    pass


def connect(dsn: str | None = None) -> psycopg.Connection:
    conn = project_documents.connect(dsn)
    conn.execute(MIGRATION.read_text(encoding="utf-8"))
    conn.commit()
    return conn


def ensure_schema(conn: psycopg.Connection) -> None:
    project_documents.ensure_schema(conn)
    conn.execute(MIGRATION.read_text(encoding="utf-8"))
    conn.commit()


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ProjectDocumentReferenceError(f"{field} is required")
    return text


def _reference_value(value: Any) -> str:
    if not isinstance(value, str):
        raise ProjectDocumentReferenceError("reference_value must be a string")
    if not value.strip():
        raise ProjectDocumentReferenceError("reference_value must be non-empty")
    return value


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProjectDocumentReferenceError(f"{field} must be a string when provided")
    text = value.strip()
    return text or None


def _validate_actor(actor: str, actor_kind: str) -> tuple[str, str]:
    actor = _required_text(actor, "actor")
    actor_kind = _required_text(actor_kind, "actor_kind")
    if actor_kind not in {"human", "system", "hermes"}:
        raise ProjectDocumentReferenceError("actor_kind must be human, system or hermes")
    if actor_kind == "hermes":
        raise GovernanceGateRequired(
            "Hermes direct issuer-reference observations are disabled; use a separately admitted candidate capability"
        )
    return actor, actor_kind


def _replay(
    conn: psycopg.Connection,
    *,
    idempotency_key: str,
    payload_digest: str,
) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT payload_digest, result_snapshot
              FROM doc_document_version_reference_observations
             WHERE idempotency_key = %s
            """,
            (idempotency_key,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    if row["payload_digest"] != payload_digest:
        raise ReferenceIdempotencyConflict(
            "idempotency key already belongs to another issuer-reference observation"
        )
    return _jsonable(dict(row["result_snapshot"]))


def _observation_row(conn: psycopg.Connection, observation_id: str) -> dict[str, Any]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT observation_id, document_version_id, reference_value,
                   basis_kind, basis_ref, observed_by, actor_kind, observed_at
              FROM doc_document_version_reference_observations
             WHERE observation_id = %s
            """,
            (observation_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise ReferenceObservationNotFound(f"unknown issuer-reference observation: {observation_id}")
    result = _jsonable(dict(row))
    result["authority"] = dict(AUTHORITY)
    return result


def record_issuer_reference(
    conn: psycopg.Connection,
    *,
    document_version_id: str,
    reference_value: str,
    basis_kind: str,
    actor: str,
    actor_kind: str,
    idempotency_key: str,
    basis_ref: str | None = None,
) -> dict[str, Any]:
    """Record one exact opaque issuer-reference observation for a revision."""
    actor, actor_kind = _validate_actor(actor, actor_kind)
    document_version_id = _required_text(document_version_id, "document_version_id")
    reference_value = _reference_value(reference_value)
    basis_kind = _required_text(basis_kind, "basis_kind")
    if basis_kind not in BASIS_KINDS:
        raise ProjectDocumentReferenceError(f"unsupported basis_kind: {basis_kind}")
    basis_ref = _optional_text(basis_ref, "basis_ref")
    idempotency_key = _required_text(idempotency_key, "idempotency_key")

    # Refuses unknown revisions through the existing professional owner.
    project_documents.get_revision(conn, document_version_id)

    payload = {
        "operation": "record_issuer_document_reference",
        "document_version_id": document_version_id,
        "reference_value": reference_value,
        "basis_kind": basis_kind,
        "basis_ref": basis_ref,
        "actor": actor,
        "actor_kind": actor_kind,
    }
    payload_digest = _digest(payload)

    with conn.transaction():
        replay = _replay(
            conn,
            idempotency_key=idempotency_key,
            payload_digest=payload_digest,
        )
        if replay is not None:
            return replay

        observation_id = f"doc-reference-observation-{uuid.uuid4().hex}"
        observed_at = conn.execute("SELECT clock_timestamp()").fetchone()[0]
        snapshot = {
            "observation_id": observation_id,
            "document_version_id": document_version_id,
            "reference_value": reference_value,
            "basis_kind": basis_kind,
            "basis_ref": basis_ref,
            "observed_by": actor,
            "actor_kind": actor_kind,
            "observed_at": _jsonable(observed_at),
            "authority": dict(AUTHORITY),
        }
        conn.execute(
            """
            INSERT INTO doc_document_version_reference_observations (
                observation_id, document_version_id, reference_value,
                basis_kind, basis_ref, observed_by, actor_kind,
                idempotency_key, payload_digest, result_snapshot, observed_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                observation_id,
                document_version_id,
                reference_value,
                basis_kind,
                basis_ref,
                actor,
                actor_kind,
                idempotency_key,
                payload_digest,
                Jsonb(snapshot),
                observed_at,
            ),
        )
        return snapshot


def list_issuer_reference_observations(
    conn: psycopg.Connection,
    document_version_id: str,
) -> list[dict[str, Any]]:
    project_documents.get_revision(conn, document_version_id)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT observation_id, document_version_id, reference_value,
                   basis_kind, basis_ref, observed_by, actor_kind, observed_at
              FROM doc_document_version_reference_observations
             WHERE document_version_id = %s
             ORDER BY observed_at, observation_id
            """,
            (document_version_id,),
        )
        rows = cur.fetchall()
    observations: list[dict[str, Any]] = []
    for row in rows:
        item = _jsonable(dict(row))
        item["authority"] = dict(AUTHORITY)
        observations.append(item)
    return observations


def resolve_issuer_document_reference(
    conn: psycopg.Connection,
    document_version_id: str,
) -> dict[str, Any]:
    """Calculate the canonical opaque issuer reference posture for one revision."""
    revision = project_documents.get_revision(conn, document_version_id)
    observations = list_issuer_reference_observations(conn, document_version_id)

    distinct: list[str] = []
    for observation in observations:
        value = observation["reference_value"]
        if value not in distinct:
            distinct.append(value)

    if not distinct:
        status = "unresolved"
        selected = None
    elif len(distinct) == 1:
        status = "resolved"
        selected = distinct[0]
    else:
        status = "conflicting"
        selected = None

    return {
        "document_id": revision["document_id"],
        "document_version_id": document_version_id,
        "resolution_status": status,
        "issuer_document_reference": selected,
        "observed_values": distinct,
        "observation_count": len(observations),
        "observations": observations,
        "limitations": [
            "reference values are opaque and case/punctuation sensitive",
            "observation chronology does not establish revision chronology or authority",
            "conflicting observations are not resolved by newest-wins",
        ],
        "authority": dict(AUTHORITY),
    }
