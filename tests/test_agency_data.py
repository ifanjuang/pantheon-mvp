"""PostgreSQL acceptance tests for native Agency Data records."""

from __future__ import annotations

import uuid

import psycopg
import pytest

from mvp_vertical import agency_data


@pytest.fixture
def conn():
    try:
        connection = agency_data.connect()
    except Exception as exc:  # pragma: no cover - local unit-only environment
        pytest.skip(f"PostgreSQL unreachable: {exc}")
    connection.execute(
        "TRUNCATE agency_project_events, agency_project_participations, agency_people, "
        "agency_organizations, agency_projects RESTART IDENTITY CASCADE"
    )
    connection.commit()
    yield connection
    connection.close()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _create(conn, *, actor_kind: str = "human") -> dict:
    return agency_data.create_project(
        conn,
        project_id=_id("project"),
        code="LIEUREY",
        display_name="Lieurey",
        description="Maison individuelle",
        status="En cours",
        phase="PRO",
        location="Lieurey",
        primary_client="Client fictif",
        tags=["Neuf", "ABF", "abf"],
        actor="reviewer" if actor_kind == "human" else "hermes-agency-adapter",
        actor_kind=actor_kind,
        idempotency_key=_id("create"),
    )


def test_project_create_list_and_revision_checked_update(conn) -> None:
    created = _create(conn)
    assert created["owner_system"] == "postgres"
    assert created["revision"] == 1
    assert created["tags"] == ["Neuf", "ABF"]

    listed = agency_data.list_projects(conn, query="lieu")
    assert [item["project_id"] for item in listed] == [created["project_id"]]

    updated = agency_data.update_project(
        conn,
        project_id=created["project_id"],
        changes={"phase": "DCE", "status": "En cours"},
        actor="hermes-agency-adapter",
        actor_kind="hermes",
        expected_revision=1,
        idempotency_key=_id("update"),
    )
    assert updated["phase"] == "DCE"
    assert updated["revision"] == 2
    assert updated["updated_by"] == "hermes-agency-adapter"


def test_stale_hermes_write_is_refused_without_overwrite(conn) -> None:
    created = _create(conn)
    agency_data.update_project(
        conn,
        project_id=created["project_id"],
        changes={"phase": "DCE"},
        actor="human-reviewer",
        actor_kind="human",
        expected_revision=1,
        idempotency_key=_id("human-update"),
    )

    with pytest.raises(agency_data.StaleProjectWrite):
        agency_data.update_project(
            conn,
            project_id=created["project_id"],
            changes={"phase": "ACT"},
            actor="hermes-agency-adapter",
            actor_kind="hermes",
            expected_revision=1,
            idempotency_key=_id("stale-hermes-update"),
        )

    assert agency_data.get_project(conn, created["project_id"])["phase"] == "DCE"


def test_idempotent_replay_returns_original_snapshot(conn) -> None:
    created = _create(conn)
    key = _id("update")
    first = agency_data.update_project(
        conn,
        project_id=created["project_id"],
        changes={"phase": "DCE"},
        actor="hermes-agency-adapter",
        actor_kind="hermes",
        expected_revision=1,
        idempotency_key=key,
    )
    replay = agency_data.update_project(
        conn,
        project_id=created["project_id"],
        changes={"phase": "DCE"},
        actor="hermes-agency-adapter",
        actor_kind="hermes",
        expected_revision=1,
        idempotency_key=key,
    )
    assert replay == first


def test_idempotency_key_cannot_be_reused_for_different_payload(conn) -> None:
    created = _create(conn)
    key = _id("update")
    agency_data.update_project(
        conn,
        project_id=created["project_id"],
        changes={"phase": "DCE"},
        actor="hermes-agency-adapter",
        actor_kind="hermes",
        expected_revision=1,
        idempotency_key=key,
    )
    with pytest.raises(agency_data.IdempotencyConflict):
        agency_data.update_project(
            conn,
            project_id=created["project_id"],
            changes={"phase": "ACT"},
            actor="hermes-agency-adapter",
            actor_kind="hermes",
            expected_revision=1,
            idempotency_key=key,
        )


def test_project_events_are_append_only(conn) -> None:
    created = _create(conn)
    event_id = conn.execute(
        "SELECT event_id FROM agency_project_events WHERE project_id = %s",
        (created["project_id"],),
    ).fetchone()[0]
    with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        conn.execute("UPDATE agency_project_events SET actor = 'rewritten' WHERE event_id = %s", (event_id,))
    conn.rollback()
    with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        conn.execute("DELETE FROM agency_project_events WHERE event_id = %s", (event_id,))
    conn.rollback()


def test_unknown_project_fields_are_refused(conn) -> None:
    created = _create(conn)
    with pytest.raises(agency_data.AgencyDataError, match="unsupported"):
        agency_data.update_project(
            conn,
            project_id=created["project_id"],
            changes={"evidence_status": "approved"},
            actor="hermes-agency-adapter",
            actor_kind="hermes",
            expected_revision=1,
            idempotency_key=_id("forbidden"),
        )
