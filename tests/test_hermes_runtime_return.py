"""Acceptance tests for normalized external Hermes returns."""

from __future__ import annotations

import uuid
import pytest

from mvp_vertical import agency_data, hermes_execution, hermes_handoff_preview, hermes_handoff_store, hermes_runtime_return, work_issues


def _id(prefix: str) -> str: return f"{prefix}-{uuid.uuid4().hex}"


@pytest.fixture
def conn():
    try:
        connection = agency_data.connect()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"PostgreSQL unreachable: {exc}")
    connection.execute(work_issues.MIGRATION.read_text(encoding="utf-8"))
    connection.execute(hermes_handoff_store.MIGRATION.read_text(encoding="utf-8"))
    for migration in hermes_execution.MIGRATIONS:
        connection.execute(migration.read_text(encoding="utf-8"))
    connection.commit()
    yield connection
    connection.close()


def _running(conn) -> tuple[dict, dict, str]:
    project = agency_data.create_project(
        conn, project_id=_id("project"), code=_id("CODE").upper(),
        display_name="Projet Hermes Return", actor="human-reviewer",
        actor_kind="human", idempotency_key=_id("project-create"),
    )
    envelope = {
        "root_entity": {"entity_id": f"project:{project['project_id']}", "entity_type": "project"},
        "descendants": [], "source_refs": [], "explicit_additions": [], "explicit_exclusions": [],
        "scope_widened_implicitly": False,
    }
    preview = hermes_handoff_preview.build_preview(
        question="Analyse le dossier.", card_context_envelope=envelope, selected_context=[]
    )
    handoff = hermes_handoff_store.submit_handoff(
        conn, actor="ifan", idempotency_key=_id("handoff-submit"), question="Analyse le dossier.",
        preview=preview, card_context_envelope=envelope, selected_context=[], include_declared_descendants=False,
    )
    admission = hermes_execution.admit_handoff(
        conn, handoff_id=handoff["handoff_id"], actor="ifan",
        idempotency_key=_id("execution-admit"), ttl_seconds=900,
    )
    run_id = _id("hermes-run")
    started = hermes_execution.record_external_runtime_start(
        conn, admission_id=admission["admission_id"], run_id=run_id, actor="hermes-adapter",
        expected_issue_version=handoff["work_issue"]["version"], idempotency_key=_id("runtime-start"),
    )
    return admission, started["work_issue"], run_id


def test_result_candidate_moves_issue_to_review_without_closing_or_admitting_evidence(conn) -> None:
    admission, issue, run_id = _running(conn)
    result = hermes_runtime_return.record_external_runtime_return(
        conn, admission_id=admission["admission_id"], run_id=run_id, actor="hermes-adapter",
        expected_issue_version=issue["version"], idempotency_key=_id("runtime-return"),
        normalized_return={
            "outcome": "result_candidate", "summary": "Analyse terminée, à relire.",
            "trace_refs": ["hermes://trace/run-1"], "source_refs": [],
            "evidence_candidate_refs": [], "limitations": [], "open_questions": [],
        },
    )
    assert result["runtime_return_recorded"] is True
    assert result["runtime_status"] == "returned"
    assert result["work_issue"]["status"] == "review"
    assert result["result_status"] == "candidate"
    assert result["evidence_admitted"] is False
    assert result["issue_closed"] is False


def test_partial_return_waits_and_same_material_event_can_replay(conn) -> None:
    admission, issue, run_id = _running(conn)
    values = dict(
        conn=conn, admission_id=admission["admission_id"], run_id=run_id,
        actor="hermes-adapter", expected_issue_version=issue["version"],
        idempotency_key=_id("runtime-return"),
        normalized_return={"outcome":"partial","summary":"Analyse partielle.","trace_refs":["hermes://trace/run-partial"]},
    )
    first = hermes_runtime_return.record_external_runtime_return(**values)
    replay = hermes_runtime_return.record_external_runtime_return(**values)
    assert first["work_issue"]["status"] == "waiting"
    assert first["runtime_status"] == "partial"
    assert replay["work_issue"]["status"] == "waiting"
    assert replay["runtime_status"] == "partial"


def test_return_for_wrong_admission_is_refused(conn) -> None:
    _, issue, run_id = _running(conn)
    with pytest.raises(hermes_runtime_return.HermesRuntimeReturnConflict):
        hermes_runtime_return.record_external_runtime_return(
            conn, admission_id="admission-wrong", run_id=run_id, actor="hermes-adapter",
            expected_issue_version=issue["version"], idempotency_key=_id("runtime-return"),
            normalized_return={"outcome":"result_candidate","summary":"Analyse.","trace_refs":["hermes://trace/run-1"]},
        )
