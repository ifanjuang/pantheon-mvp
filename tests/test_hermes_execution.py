"""Acceptance tests for the governed external Hermes execution boundary."""

from __future__ import annotations

import uuid

import pytest

from mvp_vertical import (
    agency_data,
    hermes_execution,
    hermes_handoff_preview,
    hermes_handoff_store,
    work_issues,
)


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


@pytest.fixture
def conn():
    try:
        connection = agency_data.connect()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"PostgreSQL unreachable: {exc}")
    connection.execute(work_issues.MIGRATION.read_text(encoding="utf-8"))
    connection.execute(hermes_handoff_store.MIGRATION.read_text(encoding="utf-8"))
    connection.execute(hermes_execution.MIGRATION.read_text(encoding="utf-8"))
    connection.commit()
    yield connection
    connection.close()


def _submitted_handoff(conn) -> dict:
    project = agency_data.create_project(
        conn,
        project_id=_id("project"),
        code=_id("CODE").upper(),
        display_name="Projet Hermes Execution",
        actor="human-reviewer",
        actor_kind="human",
        idempotency_key=_id("project-create"),
    )
    envelope = {
        "root_entity": {
            "entity_id": f"project:{project['project_id']}",
            "entity_type": "project",
        },
        "descendants": [],
        "source_refs": [],
        "explicit_additions": [],
        "explicit_exclusions": [],
        "scope_widened_implicitly": False,
    }
    preview = hermes_handoff_preview.build_preview(
        question="Vérifie les points structurels du dossier.",
        card_context_envelope=envelope,
        selected_context=[],
    )
    return hermes_handoff_store.submit_handoff(
        conn,
        actor="ifan",
        idempotency_key=_id("handoff-submit"),
        question="Vérifie les points structurels du dossier.",
        preview=preview,
        card_context_envelope=envelope,
        selected_context=[],
        include_declared_descendants=False,
    )


def test_human_admission_is_immutable_and_does_not_start_runtime(conn) -> None:
    handoff = _submitted_handoff(conn)
    admission = hermes_execution.admit_handoff(
        conn,
        handoff_id=handoff["handoff_id"],
        actor="ifan",
        idempotency_key=_id("execution-admit"),
    )

    assert admission["decision"] == "allow"
    assert admission["requested_effect"] == "read_only"
    assert admission["ready_for_external_runtime"] is True
    assert admission["runtime_started"] is False
    assert admission["consumed_by_run_id"] is None

    run_count = conn.execute(
        "SELECT count(*) FROM hermes_runs WHERE issue_id = %s",
        (handoff["work_issue"]["issue_id"],),
    ).fetchone()[0]
    assert run_count == 0

    with pytest.raises(Exception, match="hermes_execution_admissions are immutable"):
        conn.execute(
            "UPDATE hermes_execution_admissions SET admitted_by = 'rewritten' WHERE admission_id = %s",
            (admission["admission_id"],),
        )
    conn.rollback()


def test_execution_envelope_is_exact_pull_by_id_not_queue(conn) -> None:
    handoff = _submitted_handoff(conn)
    admission = hermes_execution.admit_handoff(
        conn,
        handoff_id=handoff["handoff_id"],
        actor="ifan",
        idempotency_key=_id("execution-admit"),
    )
    envelope = hermes_execution.get_execution_envelope(conn, admission["admission_id"])

    assert envelope["kind"] == "hermes_execution_envelope"
    assert envelope["admission"]["admission_id"] == admission["admission_id"]
    assert envelope["task_contract"]["task_contract_ref"] == handoff["task_contract_ref"]
    assert envelope["context_pack"]["context_pack_ref"] == handoff["context_pack_ref"]
    assert envelope["runtime_instruction"] is None
    assert envelope["dispatch_requested"] is False


def test_external_hermes_reports_its_own_run_and_consumes_admission_once(conn) -> None:
    handoff = _submitted_handoff(conn)
    admission = hermes_execution.admit_handoff(
        conn,
        handoff_id=handoff["handoff_id"],
        actor="ifan",
        idempotency_key=_id("execution-admit"),
    )
    issue = handoff["work_issue"]
    run_id = _id("hermes-runtime")

    started = hermes_execution.record_external_runtime_start(
        conn,
        admission_id=admission["admission_id"],
        run_id=run_id,
        actor="hermes-adapter",
        expected_issue_version=issue["version"],
        idempotency_key=_id("runtime-start"),
    )

    assert started["runtime_start_recorded"] is True
    assert started["replayed"] is False
    assert started["work_issue"]["status"] == "in_progress"

    row = conn.execute(
        "SELECT run_id, status, admission_ref FROM hermes_runs WHERE run_id = %s",
        (run_id,),
    ).fetchone()
    assert row == (run_id, "running", admission["admission_id"])

    replay = hermes_execution.record_external_runtime_start(
        conn,
        admission_id=admission["admission_id"],
        run_id=run_id,
        actor="hermes-adapter",
        expected_issue_version=issue["version"],
        idempotency_key=_id("runtime-replay"),
    )
    assert replay["replayed"] is True

    with pytest.raises(hermes_execution.RuntimeStartConflict):
        hermes_execution.record_external_runtime_start(
            conn,
            admission_id=admission["admission_id"],
            run_id=_id("other-run"),
            actor="hermes-adapter",
            expected_issue_version=issue["version"],
            idempotency_key=_id("runtime-conflict"),
        )
