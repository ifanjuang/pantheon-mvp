"""Normalize an external Hermes return against one consumed execution admission.

This adapter records candidate runtime output only. It never closes the Work Issue,
admits Evidence, promotes memory or authorizes a consequential effect.
"""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from . import work_issues


class HermesRuntimeReturnError(ValueError):
    pass


class HermesRuntimeReturnConflict(HermesRuntimeReturnError):
    pass


def _run_for_admission(
    conn: psycopg.Connection,
    *,
    admission_id: str,
    run_id: str,
) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT r.*, a.work_issue_id
              FROM hermes_runs r
              JOIN hermes_execution_admissions a ON a.admission_id = r.admission_ref
             WHERE r.run_id = %s
               AND r.admission_ref = %s
            """,
            (run_id, admission_id),
        )
        row = cur.fetchone()
    if row is None:
        raise HermesRuntimeReturnConflict(
            "Hermes return does not match a run consumed under this execution admission"
        )
    return dict(row)


def record_external_runtime_return(
    conn: psycopg.Connection,
    *,
    admission_id: str,
    run_id: str,
    normalized_return: dict,
    actor: str,
    expected_issue_version: int,
    idempotency_key: str,
) -> dict:
    if not actor.strip():
        raise HermesRuntimeReturnError("Hermes actor is required")
    if not run_id.strip():
        raise HermesRuntimeReturnError("external Hermes run_id is required")

    with conn.transaction():
        run = _run_for_admission(conn, admission_id=admission_id, run_id=run_id)
        if run["status"] != "running":
            # A matching returned/partial/failed run is a replay only when the same
            # material return event already exists; work_issues owns that idempotency.
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM issue_events WHERE issue_id = %s AND idempotency_key = %s",
                    (run["work_issue_id"], idempotency_key),
                )
                if cur.fetchone() is None:
                    raise HermesRuntimeReturnConflict(
                        f"Hermes run is not running; current runtime status is {run['status']}"
                    )

        issue = work_issues.get_issue(conn, run["work_issue_id"])
        if issue["version"] != expected_issue_version and run["status"] == "running":
            raise HermesRuntimeReturnConflict(
                f"stale Work Issue version: expected {expected_issue_version}, current {issue['version']}"
            )

        try:
            updated_issue = work_issues.record_hermes_return(
                conn,
                issue_id=run["work_issue_id"],
                run_id=run_id,
                normalized_return=normalized_return,
                actor=actor.strip(),
                expected_version=expected_issue_version,
                idempotency_key=idempotency_key,
            )
        except (work_issues.StaleWrite, work_issues.TransitionRefused) as exc:
            raise HermesRuntimeReturnConflict(str(exc)) from exc
        except work_issues.WorkIssueError as exc:
            raise HermesRuntimeReturnError(str(exc)) from exc

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM hermes_runs WHERE run_id = %s", (run_id,))
            returned_run = dict(cur.fetchone())

        return {
            "admission_id": admission_id,
            "run_id": run_id,
            "runtime_return_recorded": True,
            "runtime_status": returned_run["status"],
            "work_issue": updated_issue,
            "result_status": "candidate",
            "evidence_admitted": False,
            "issue_closed": updated_issue["status"] in {"done", "cancelled"},
            "non_equivalences": [
                "Hermes returned != Work Issue resolved",
                "runtime return != Evidence admitted",
                "result candidate != canonical truth",
                "runtime success != governance success",
            ],
        }
