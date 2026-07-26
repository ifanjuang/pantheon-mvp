"""Read-only Work Issue projections for the cards-first cockpit.

The adapter reads the existing Work Issue aggregate and append-only events. It
creates no card record, changes no issue status and grants no Hermes authority.
"""

from __future__ import annotations

import psycopg

from . import work_issues


_STATUS_ORDER = {
    "review": 0,
    "waiting": 1,
    "open": 2,
    "in_progress": 3,
    "done": 4,
    "cancelled": 5,
}


def _card_projection(issue: dict) -> dict:
    """Expose workflow metadata without turning it into an execution engine."""
    projected = dict(issue)
    workflow = issue.get("workflow") if isinstance(issue.get("workflow"), dict) else {}
    decision = (
        issue.get("decision_request")
        if isinstance(issue.get("decision_request"), dict)
        else {}
    )

    projected["objective"] = workflow.get("objective") or issue.get("description")
    projected["milestones"] = workflow.get("milestones") or []
    projected["responsibilities"] = workflow.get("responsibilities") or []
    projected["skills"] = workflow.get("skills") or []
    projected["functions"] = workflow.get("functions") or []
    projected["tools"] = workflow.get("tools") or []
    projected["information_ref"] = issue.get("information_ref")
    projected["result_ref"] = issue.get("result_ref")
    projected["decision_title"] = decision.get("title")
    projected["decision_question"] = decision.get("question")
    projected["result_summary"] = decision.get("result_summary")
    projected["decision_options"] = decision.get("options") or []
    return projected


def get_issue_record(conn: psycopg.Connection, issue_id: str) -> dict:
    """Return the Work Issue record with read-only card projection fields."""
    projection = work_issues.get_issue(conn, issue_id)
    issue = projection.get("work_issue")
    if not isinstance(issue, dict):
        raise work_issues.WorkIssueError(
            "stored Work Issue projection is missing its work_issue record"
        )
    return _card_projection(issue)


def list_issue_projections(
    conn: psycopg.Connection,
    case_ref: str,
    *,
    include_terminal: bool = True,
    limit: int = 100,
) -> list[dict]:
    """Return governed Work Issue aggregates for one exact case reference.

    `case_ref` is matched exactly. The function does not infer project identity,
    traverse parents or broaden scope. Workflow metadata is exposed only as a
    read projection for the Cockpit; it does not schedule, dispatch or authorize.
    """
    if not case_ref.strip():
        raise work_issues.WorkIssueError("case_ref is required")
    if limit < 1 or limit > 500:
        raise work_issues.WorkIssueError("limit must be between 1 and 500")

    terminal_filter = "" if include_terminal else "AND status NOT IN ('done', 'cancelled')"
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT issue_id
              FROM work_issues
             WHERE case_ref = %s
               {terminal_filter}
             ORDER BY updated_at DESC, issue_id ASC
             LIMIT %s
            """,
            (case_ref, limit),
        )
        issue_ids = [row[0] for row in cur.fetchall()]

    projections = [work_issues.get_issue(conn, issue_id) for issue_id in issue_ids]
    for projection in projections:
        issue = projection.get("work_issue")
        if isinstance(issue, dict):
            projection["work_issue"] = _card_projection(issue)

    projections.sort(
        key=lambda projection: _STATUS_ORDER.get(
            projection["work_issue"]["status"], 99
        )
    )
    return projections
