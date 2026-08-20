"""Concurrency and referential-integrity tests for Agency Data classification."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import threading
import time

import psycopg
import pytest
from pydantic import ValidationError

from mvp_vertical import (
    agency_classification,
    agency_data,
    project_documents,
    store,
    work_issues,
)
from mvp_vertical.agency_classification_api import CategoryUpdateBody


@pytest.fixture
def conn():
    try:
        connection = store.connect()
    except Exception as exc:  # pragma: no cover - local unit-only environment
        pytest.skip(f"PostgreSQL unreachable: {exc}")
    connection.execute(work_issues.MIGRATION.read_text(encoding="utf-8"))
    connection.execute(agency_data.MIGRATION.read_text(encoding="utf-8"))
    connection.execute(project_documents.MIGRATION.read_text(encoding="utf-8"))
    connection.execute(agency_classification.MIGRATION.read_text(encoding="utf-8"))
    connection.execute(
        """
        TRUNCATE agency_category_assignments, agency_categories,
                 knowledge_items, extraction_runs, document_versions, source_documents,
                 doc_document_events, doc_document_versions, doc_documents,
                 issue_events, hermes_runs, issue_comments, work_card_metadata, work_issues,
                 agency_information_cards, agency_people, agency_organizations, agency_projects
        RESTART IDENTITY CASCADE
        """
    )
    connection.commit()
    yield connection
    connection.close()


def _project(conn, project_id: str = "project-integrity") -> str:
    conn.execute(
        """
        INSERT INTO agency_projects (
            project_id, code, display_name, created_by, updated_by
        ) VALUES (%s, %s, %s, 'human:ifj', 'human:ifj')
        """,
        (project_id, project_id.upper(), "Projet intégrité"),
    )
    conn.commit()
    return project_id


def _information(conn, project_id: str, information_id: str = "information-integrity") -> str:
    conn.execute(
        """
        INSERT INTO agency_information_cards (
            information_id, series_id, project_id, title, category,
            source_type, source_note, index_label, status
        ) VALUES (%s, %s, %s, 'Note projet', 'legacy-category', 'draft',
                  'Texte source', 'A01', 'draft')
        """,
        (information_id, f"series-{information_id}", project_id),
    )
    conn.commit()
    return information_id


def _category(
    conn,
    category_id: str,
    *,
    applies_to: list[str] | None = None,
) -> dict:
    return agency_classification.create_category(
        conn,
        category_id=category_id,
        title=category_id.title(),
        applies_to=applies_to or ["document"],
        actor="human:ifj",
    )


def test_category_update_body_distinguishes_omitted_sort_order_from_explicit_null() -> None:
    body = CategoryUpdateBody.model_validate({"expected_revision": 1})
    assert body.sort_order is None

    with pytest.raises(ValidationError, match="sort_order cannot be null"):
        CategoryUpdateBody.model_validate({"expected_revision": 1, "sort_order": None})


def test_concurrent_opposite_parent_moves_cannot_commit_a_cycle(conn) -> None:
    _category(conn, "category-a")
    _category(conn, "category-b")

    first = store.connect()
    second = store.connect()
    started = threading.Event()
    try:
        first.execute("SET LOCAL lock_timeout = '3s'")
        first.execute(
            """
            UPDATE agency_categories
               SET parent_category_id = 'category-b',
                   revision = revision + 1,
                   updated_at = clock_timestamp()
             WHERE category_id = 'category-a'
            """
        )

        def move_b_under_a():
            try:
                second.execute("SET LOCAL lock_timeout = '3s'")
                started.set()
                second.execute(
                    """
                    UPDATE agency_categories
                       SET parent_category_id = 'category-a',
                           revision = revision + 1,
                           updated_at = clock_timestamp()
                     WHERE category_id = 'category-b'
                    """
                )
                second.commit()
                return None
            except Exception as exc:  # returned to the asserting thread
                second.rollback()
                return exc

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(move_b_under_a)
            assert started.wait(timeout=1)
            time.sleep(0.05)
            assert future.done() is False
            first.commit()
            error = future.result(timeout=4)

        assert isinstance(error, psycopg.errors.RaiseException)
        assert "cycle is forbidden" in str(error)
        rows = dict(
            conn.execute(
                "SELECT category_id, parent_category_id FROM agency_categories"
            ).fetchall()
        )
        assert rows == {"category-a": "category-b", "category-b": None}
    finally:
        if first.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
            first.rollback()
        if second.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
            second.rollback()
        first.close()
        second.close()


def test_assignment_waits_for_category_archive_and_then_refuses_stale_admission(conn) -> None:
    project_id = _project(conn)
    _category(conn, "urbanisme", applies_to=["project"])

    archiver = store.connect()
    assigner = store.connect()
    started = threading.Event()
    try:
        archiver.execute("SET LOCAL lock_timeout = '3s'")
        archiver.execute(
            """
            UPDATE agency_categories
               SET archived_at = clock_timestamp(),
                   revision = revision + 1,
                   updated_at = clock_timestamp()
             WHERE category_id = 'urbanisme'
            """
        )

        def assign_after_archive_starts():
            try:
                assigner.execute("SET LOCAL lock_timeout = '3s'")
                started.set()
                assigner.execute(
                    """
                    INSERT INTO agency_category_assignments (
                        assignment_id, category_id, entity_type, entity_id, assigned_by
                    ) VALUES (
                        'assignment-race', 'urbanisme', 'project', %s, 'human:ifj'
                    )
                    """,
                    (project_id,),
                )
                assigner.commit()
                return None
            except Exception as exc:  # returned to the asserting thread
                assigner.rollback()
                return exc

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(assign_after_archive_starts)
            assert started.wait(timeout=1)
            time.sleep(0.05)
            assert future.done() is False
            archiver.commit()
            error = future.result(timeout=4)

        assert isinstance(error, psycopg.errors.RaiseException)
        assert "cannot assign an archived Category" in str(error)
        assert conn.execute(
            "SELECT count(*) FROM agency_category_assignments WHERE assignment_id = 'assignment-race'"
        ).fetchone()[0] == 0
    finally:
        if archiver.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
            archiver.rollback()
        if assigner.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
            assigner.rollback()
        archiver.close()
        assigner.close()


def test_active_assignments_block_owner_deletion_including_project_cascades(conn) -> None:
    project_id = _project(conn)
    information_id = _information(conn, project_id)
    _category(conn, "project-notes", applies_to=["information"])
    agency_classification.assign_category(
        conn,
        assignment_id="assignment-information",
        category_id="project-notes",
        entity_type="information",
        entity_id=information_id,
        actor="human:ifj",
    )

    expected_triggers = {
        "agency_projects_category_assignment_delete_guard",
        "agency_information_category_assignment_delete_guard",
        "doc_documents_category_assignment_delete_guard",
        "knowledge_items_category_assignment_delete_guard",
        "work_issues_category_assignment_delete_guard",
    }
    installed_triggers = {
        row[0]
        for row in conn.execute(
            """
            SELECT tgname
              FROM pg_trigger
             WHERE tgname = ANY(%s)
               AND NOT tgisinternal
            """,
            (list(expected_triggers),),
        ).fetchall()
    }
    assert installed_triggers == expected_triggers

    with pytest.raises(
        psycopg.errors.RaiseException,
        match="active CategoryAssignment must be retired before deleting information",
    ):
        with conn.transaction():
            conn.execute("DELETE FROM agency_projects WHERE project_id = %s", (project_id,))

    assert conn.execute(
        "SELECT count(*) FROM agency_projects WHERE project_id = %s", (project_id,)
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT count(*) FROM agency_information_cards WHERE information_id = %s",
        (information_id,),
    ).fetchone()[0] == 1
