"""Governed bridge between a submitted Cockpit handoff and an external Hermes run.

Pantheon records an immutable execution admission and validates runtime callbacks.
It does not dispatch Hermes, expose a pending-work queue, choose providers, retry
runs or schedule execution. The external Hermes adapter owns the actual start.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from . import work_issues

MIGRATION = Path(__file__).resolve().parent / "sql" / "004_hermes_execution_admissions.sql"


class HermesExecutionError(ValueError):
    pass


class AdmissionNotFound(HermesExecutionError):
    pass


class AdmissionConflict(HermesExecutionError):
    pass


class RuntimeStartConflict(HermesExecutionError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _handoff_row(conn: psycopg.Connection, handoff_id: str, *, lock: bool = False) -> dict:
    suffix = " FOR UPDATE" if lock else ""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT * FROM cockpit_hermes_handoffs WHERE handoff_id = %s{suffix}",
            (handoff_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise AdmissionNotFound(f"unknown Cockpit Hermes handoff: {handoff_id}")
    return dict(row)


def _admission_row(conn: psycopg.Connection, admission_id: str, *, lock: bool = False) -> dict:
    suffix = " FOR UPDATE" if lock else ""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT * FROM hermes_execution_admissions WHERE admission_id = %s{suffix}",
            (admission_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise AdmissionNotFound(f"unknown Hermes execution admission: {admission_id}")
    return dict(row)


def _existing_admission_by_idempotency(
    conn: psycopg.Connection, idempotency_key: str
) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM hermes_execution_admissions WHERE idempotency_key = %s",
            (idempotency_key,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def _run_for_admission(conn: psycopg.Connection, admission_id: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM hermes_runs WHERE admission_ref = %s",
            (admission_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def _admission_projection(conn: psycopg.Connection, admission: dict) -> dict:
    issue = work_issues.get_issue(conn, admission["work_issue_id"])
    run = _run_for_admission(conn, admission["admission_id"])
    return {
        "admission_id": admission["admission_id"],
        "handoff_id": admission["handoff_id"],
        "work_issue_id": admission["work_issue_id"],
        "decision": admission["decision"],
        "requested_effect": admission["requested_effect"],
        "task_contract_ref": admission["task_contract_ref"],
        "context_pack_ref": admission["context_pack_ref"],
        "preview_digest": admission["preview_digest"],
        "admission_digest": admission["admission_digest"],
        "admitted_by": admission["admitted_by"],
        "admitted_at": admission["admitted_at"].isoformat(),
        "ready_for_external_runtime": run is None and issue["status"] == "open",
        "consumed_by_run_id": run["run_id"] if run else None,
        "runtime_started": run is not None,
        "work_issue": issue,
        "non_equivalences": [
            "admission != dispatch",
            "admission != Hermes run",
            "runtime start != Evidence",
            "runtime success != governance success",
        ],
    }


def admit_handoff(
    conn: psycopg.Connection,
    *,
    handoff_id: str,
    actor: str,
    idempotency_key: str,
) -> dict:
    """Admit exactly one submitted read-only handoff for one external runtime start."""
    if not actor or not actor.strip():
        raise HermesExecutionError("human actor is required for execution admission")
    if len(idempotency_key.strip()) < 8:
        raise HermesExecutionError("idempotency_key must contain at least 8 characters")

    with conn.transaction():
        existing = _existing_admission_by_idempotency(conn, idempotency_key)
        if existing is not None:
            if existing["handoff_id"] != handoff_id or existing["admitted_by"] != actor.strip():
                raise AdmissionConflict(
                    "idempotency key already belongs to another execution admission"
                )
            return _admission_projection(conn, existing)

        handoff = _handoff_row(conn, handoff_id, lock=True)
        issue = work_issues.get_issue(conn, handoff["work_issue_id"])
        if issue["assigned_to"] != "hermes":
            raise AdmissionConflict("Work Issue is not assigned to Hermes")
        if issue["requested_effect"] != "read_only" or handoff["requested_effect"] != "read_only":
            raise AdmissionConflict("first execution-admission slice accepts read_only work only")
        if issue["status"] != "open":
            raise AdmissionConflict("execution admission requires an open Work Issue")
        if issue["task_contract_ref"] != handoff["task_contract_ref"]:
            raise AdmissionConflict("Work Issue Task Contract no longer matches the handoff snapshot")
        if issue["context_pack_ref"] != handoff["context_pack_ref"]:
            raise AdmissionConflict("Work Issue Context Pack no longer matches the handoff snapshot")
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM hermes_runs WHERE issue_id = %s LIMIT 1",
                (issue["issue_id"],),
            )
            if cur.fetchone() is not None:
                raise AdmissionConflict("Work Issue already has a Hermes run")
            cur.execute(
                "SELECT 1 FROM hermes_execution_admissions WHERE handoff_id = %s LIMIT 1",
                (handoff_id,),
            )
            if cur.fetchone() is not None:
                raise AdmissionConflict("handoff already has an execution admission")

        admission_id = f"admission-{uuid.uuid4().hex}"
        admission_basis = {
            "handoff_id": handoff_id,
            "work_issue_id": issue["issue_id"],
            "decision": "allow",
            "requested_effect": "read_only",
            "task_contract_ref": handoff["task_contract_ref"],
            "context_pack_ref": handoff["context_pack_ref"],
            "preview_digest": handoff["preview_digest"],
            "handoff_request_digest": handoff["request_digest"],
            "admitted_by": actor.strip(),
        }
        admission_digest = _digest(admission_basis)
        conn.execute(
            """
            INSERT INTO hermes_execution_admissions (
                admission_id, handoff_id, work_issue_id, decision, requested_effect,
                task_contract_ref, context_pack_ref, preview_digest,
                handoff_request_digest, admission_digest, idempotency_key, admitted_by
            ) VALUES (%s, %s, %s, 'allow', 'read_only', %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                admission_id,
                handoff_id,
                issue["issue_id"],
                handoff["task_contract_ref"],
                handoff["context_pack_ref"],
                handoff["preview_digest"],
                handoff["request_digest"],
                admission_digest,
                idempotency_key,
                actor.strip(),
            ),
        )
        admission = _admission_row(conn, admission_id)
        return _admission_projection(conn, admission)


def get_execution_envelope(conn: psycopg.Connection, admission_id: str) -> dict:
    """Return one exact admitted envelope by ID; never list or queue pending work."""
    admission = _admission_row(conn, admission_id)
    handoff = _handoff_row(conn, admission["handoff_id"])
    projection = _admission_projection(conn, admission)
    if handoff["task_contract_ref"] != admission["task_contract_ref"]:
        raise AdmissionConflict("admission Task Contract does not match immutable handoff")
    if handoff["context_pack_ref"] != admission["context_pack_ref"]:
        raise AdmissionConflict("admission Context Pack does not match immutable handoff")
    if handoff["preview_digest"] != admission["preview_digest"]:
        raise AdmissionConflict("admission preview digest does not match immutable handoff")
    return {
        "kind": "hermes_execution_envelope",
        "admission": projection,
        "task_contract": handoff["task_contract"],
        "context_pack": handoff["context_pack"],
        "question": handoff["question"],
        "selected_context": list(handoff["selected_context"] or []),
        "runtime_instruction": None,
        "dispatch_requested": False,
    }


def record_external_runtime_start(
    conn: psycopg.Connection,
    *,
    admission_id: str,
    run_id: str,
    actor: str,
    expected_issue_version: int,
    idempotency_key: str,
) -> dict:
    """Record a run that the external Hermes adapter has started itself."""
    if not run_id.strip():
        raise HermesExecutionError("external Hermes run_id is required")
    if not actor.strip():
        raise HermesExecutionError("Hermes actor is required")

    with conn.transaction():
        admission = _admission_row(conn, admission_id, lock=True)
        existing_run = _run_for_admission(conn, admission_id)
        if existing_run is not None:
            if existing_run["run_id"] != run_id:
                raise RuntimeStartConflict("execution admission has already been consumed by another run")
            return {
                "admission_id": admission_id,
                "run_id": existing_run["run_id"],
                "runtime_start_recorded": True,
                "replayed": True,
                "work_issue": work_issues.get_issue(conn, admission["work_issue_id"]),
            }

        issue = work_issues.get_issue(conn, admission["work_issue_id"])
        if issue["version"] != expected_issue_version:
            raise RuntimeStartConflict(
                f"stale Work Issue version: expected {expected_issue_version}, current {issue['version']}"
            )
        if issue["status"] != "open":
            raise RuntimeStartConflict("external Hermes start requires an open Work Issue")
        if issue["assigned_to"] != "hermes":
            raise RuntimeStartConflict("Work Issue is not assigned to Hermes")
        if issue["task_contract_ref"] != admission["task_contract_ref"]:
            raise RuntimeStartConflict("Task Contract changed after execution admission")
        if issue["context_pack_ref"] != admission["context_pack_ref"]:
            raise RuntimeStartConflict("Context Pack changed after execution admission")

        started_issue = work_issues.start_hermes_run(
            conn,
            issue_id=issue["issue_id"],
            run_id=run_id,
            task_contract_ref=admission["task_contract_ref"],
            context_pack_ref=admission["context_pack_ref"],
            actor=actor.strip(),
            expected_version=expected_issue_version,
            idempotency_key=idempotency_key,
        )
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE hermes_runs SET admission_ref = %s WHERE run_id = %s AND admission_ref IS NULL",
                (admission_id, run_id),
            )
            if cur.rowcount != 1:
                raise RuntimeStartConflict("Hermes run admission linkage could not be recorded")

        return {
            "admission_id": admission_id,
            "run_id": run_id,
            "runtime_start_recorded": True,
            "replayed": False,
            "work_issue": started_issue,
            "non_equivalences": [
                "runtime start recorded != Evidence",
                "running != task success",
                "task success != governance success",
            ],
        }
