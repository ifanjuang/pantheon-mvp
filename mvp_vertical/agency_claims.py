"""Agency Data seam: project claims that cite their backing card.

A ``project_claim`` is a typed, status-qualified value shown on a Project Card
that CITES the card proving it (Document, Evidence, Knowledge, Décision,
Surface/Fact, Jalon or Participation). It is the executable side of the
card-deck composition rule: the value is never authoritative on its own — it
points at the backing card.

This module is bounded internal persistence and a read-only projection. It is
NOT an approval, Evidence-admission or promotion engine:

    stored claim != approved value
    source_backed != verified != opposable
    persistence != Evidence admission

The emitted record conforms to the vendored governance contract
``vendor/pantheon/project_claim.schema.yaml`` (upstream
``schemas/project_claim.schema.yaml``). Every read re-validates against that
contract, so a stored row that violates it is a loud failure, not a silent one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import psycopg
import yaml
from psycopg.rows import dict_row

from .store import dsn_from_env


MIGRATION = Path(__file__).resolve().parent / "sql" / "002_project_claims.sql"
SCHEMA = (
    Path(__file__).resolve().parent
    / "vendor"
    / "pantheon"
    / "project_claim.schema.yaml"
)

GOVERNANCE_REFS = [
    "docs/domain-packs/architecture/PROJECT_CARD_DECK_COMPOSITION.md",
    "docs/governance/AGENCY_DATA_SYSTEM_OF_RECORD.md",
    "docs/governance/CARD_STACK_MODEL.md",
]

# A claim never carries an "approved"/"opposable" value: the schema enum has no
# such member, and this mirror keeps the intent explicit at the write boundary.
CLAIM_STATUSES = {"asserted", "source_backed", "verified", "contested", "retired"}


class AgencyClaimError(ValueError):
    """Base refusal for the bounded project-claim adapter."""


class ClaimContractViolation(AgencyClaimError):
    """A claim payload or stored row does not conform to the governed contract."""


def _schema() -> dict[str, Any]:
    return yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))


def _validator() -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(
        _schema(), format_checker=jsonschema.FormatChecker()
    )


def validate_claim(claim: dict) -> None:
    """Validate one claim record against the vendored governance contract."""
    try:
        _validator().validate(claim)
    except jsonschema.ValidationError as exc:
        raise ClaimContractViolation(
            f"project claim violates its governed contract: {exc.message}"
        ) from exc


def connect(dsn: str | None = None) -> psycopg.Connection:
    conn = psycopg.connect(dsn or dsn_from_env())
    conn.execute(MIGRATION.read_text(encoding="utf-8"))
    conn.commit()
    return conn


def _iso(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _row_to_claim(row: dict) -> dict:
    """Project one stored row into a schema-conforming claim record.

    Emits ONLY the keys the governed schema defines (it sets
    ``additionalProperties: false``); optional fields are emitted as ``null``.
    """
    backing = {
        "card_family": row["card_family"],
        "card_id": row["card_id"],
        "card_status": row["card_status"],
    }
    provenance = {
        "source_kind": row["source_kind"],
        "source_ref": row["source_ref"],
        "asserted_by": row["asserted_by"],
        "derivation_note": row["derivation_note"],
    }
    return {
        "claim_id": row["claim_id"],
        "project_id": row["project_id"],
        "claim_type": row["claim_type"],
        "value": row["value"],
        "unit": row["unit"],
        "backing_card_ref": backing,
        "provenance": provenance,
        "status": row["status"],
        "observed_at": _iso(row["observed_at"]),
        "revision": row["revision"],
        "supersedes": row["supersedes"],
        "note": row["note"],
        "governance_refs": list(GOVERNANCE_REFS),
    }


def record_claim(
    conn: psycopg.Connection,
    *,
    claim_id: str,
    project_id: str,
    claim_type: str,
    value: Any,
    backing_card_ref: dict,
    provenance: dict,
    status: str,
    observed_at: str,
    unit: str | None = None,
    revision: int = 0,
    supersedes: str | None = None,
    note: str | None = None,
) -> dict:
    """Persist one project claim candidate, contract-validated before write.

    This records a claim; it approves nothing, admits no Evidence and promotes
    no value. The claim is stored with its provenance and backing-card citation
    and returned as a re-read, re-validated projection.
    """
    if status not in CLAIM_STATUSES:
        raise AgencyClaimError(f"unknown claim status: {status!r}")
    if not isinstance(backing_card_ref, dict):
        raise AgencyClaimError("backing_card_ref must be an object")
    if not isinstance(provenance, dict):
        raise AgencyClaimError("provenance must be an object")

    candidate = {
        "claim_id": claim_id,
        "project_id": project_id,
        "claim_type": claim_type,
        "value": value,
        "unit": unit,
        "backing_card_ref": {
            "card_family": backing_card_ref.get("card_family"),
            "card_id": backing_card_ref.get("card_id"),
            "card_status": backing_card_ref.get("card_status"),
        },
        "provenance": {
            "source_kind": provenance.get("source_kind"),
            "source_ref": provenance.get("source_ref"),
            "asserted_by": provenance.get("asserted_by"),
            "derivation_note": provenance.get("derivation_note"),
        },
        "status": status,
        "observed_at": observed_at,
        "revision": revision,
        "supersedes": supersedes,
        "note": note,
        "governance_refs": list(GOVERNANCE_REFS),
    }
    # Fail fast on the governed contract before any write touches the database.
    validate_claim(candidate)

    with conn.transaction():
        conn.execute(
            """
            INSERT INTO agency.project_claim (
                claim_id, project_id, claim_type, value, unit,
                card_family, card_id, card_status,
                source_kind, source_ref, asserted_by, derivation_note,
                status, observed_at, revision, supersedes, note
            ) VALUES (
                %s, %s, %s, %s::jsonb, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            """,
            (
                claim_id,
                project_id,
                claim_type,
                json.dumps(value),
                unit,
                candidate["backing_card_ref"]["card_family"],
                candidate["backing_card_ref"]["card_id"],
                candidate["backing_card_ref"]["card_status"],
                candidate["provenance"]["source_kind"],
                candidate["provenance"]["source_ref"],
                candidate["provenance"]["asserted_by"],
                candidate["provenance"]["derivation_note"],
                status,
                observed_at,
                revision,
                supersedes,
                note,
            ),
        )
    return get_claim(conn, claim_id)


def get_claim(conn: psycopg.Connection, claim_id: str) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM agency.project_claim WHERE claim_id = %s", (claim_id,)
        )
        row = cur.fetchone()
    if row is None:
        raise AgencyClaimError(f"unknown project claim: {claim_id}")
    claim = _row_to_claim(row)
    validate_claim(claim)
    return claim


def list_project_claims(
    conn: psycopg.Connection,
    project_id: str,
    *,
    include_retired: bool = True,
    limit: int = 200,
) -> list[dict]:
    """Return governed project-claim projections for one exact project id.

    ``project_id`` is matched exactly; the reader infers no identity and
    broadens no scope. Each returned record is re-validated against the governed
    contract before it leaves this function.
    """
    if not project_id.strip():
        raise AgencyClaimError("project_id is required")
    if limit < 1 or limit > 500:
        raise AgencyClaimError("limit must be between 1 and 500")

    retired_filter = "" if include_retired else "AND status <> 'retired'"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT *
              FROM agency.project_claim
             WHERE project_id = %s
               {retired_filter}
             ORDER BY claim_type ASC, observed_at DESC, claim_id ASC
             LIMIT %s
            """,
            (project_id, limit),
        )
        rows = [dict(row) for row in cur.fetchall()]

    claims = [_row_to_claim(row) for row in rows]
    for claim in claims:
        validate_claim(claim)
    return claims
