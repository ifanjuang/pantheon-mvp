"""Apply the bounded A/B and Entity relation convergence patch.

This temporary script is branch-scoped and deletes itself before the resulting
commit. Every replacement asserts the observed owner shape and fails closed if
that shape changed.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def rename_information_migration() -> None:
    old = ROOT / "mvp_vertical/sql/012_information_card_projection.sql"
    new = ROOT / "mvp_vertical/sql/013_information_card_projection.sql"
    if old.exists():
        old.rename(new)
    if not new.exists():
        raise SystemExit("Information projection migration is missing")
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix not in {".py", ".md", ".sql", ".yml", ".yaml"}:
            continue
        value = path.read_text(encoding="utf-8")
        if "012_information_card_projection.sql" in value:
            path.write_text(
                value.replace(
                    "012_information_card_projection.sql",
                    "013_information_card_projection.sql",
                ),
                encoding="utf-8",
            )


def patch_knowledge_projection() -> None:
    path = "mvp_vertical/knowledge_edit_variants.py"
    text = read(path)
    text = replace_once(
        text,
        "def project_execution_result_variant(\n",
        "def _project_execution_result_variant_inner(\n",
        "rename Knowledge projection owner",
    )
    old = '''    if not required.issubset(payload):
        raise KnowledgeEditVariantError("Knowledge edit variant payload is incomplete")
'''
    new = '''    if not required.issubset(payload):
        raise KnowledgeEditVariantError("Knowledge edit variant payload is incomplete")
    allowed = required | {"rationale", "source_refs", "limitations"}
    unknown = set(payload) - allowed
    if unknown:
        raise KnowledgeEditVariantError(
            "Knowledge edit variant payload has unsupported fields: "
            + ", ".join(sorted(unknown))
        )
'''
    text = replace_once(text, old, new, "close Knowledge candidate payload")
    if "def project_execution_result_variant(" in text:
        raise SystemExit("Knowledge projection wrapper still exists after owner rename")
    text += '''


def project_execution_result_variant(
    conn: psycopg.Connection,
    *,
    execution_result_id: str,
    result_ref: str,
    idempotency_key: str,
) -> dict[str, Any]:
    """Project a candidate and persist a stale-scope conflict after rollback."""
    try:
        return _project_execution_result_variant_inner(
            conn,
            execution_result_id=execution_result_id,
            result_ref=result_ref,
            idempotency_key=idempotency_key,
        )
    except KnowledgeEditVariantConflict:
        result = _execution_result_item(conn, execution_result_id, result_ref)
        request_id = str(dict(result.get("payload") or {}).get("request_ref") or "")
        if request_id:
            try:
                request = _request_row(conn, request_id)
                item = _knowledge_snapshot(conn, request["knowledge_id"])
            except knowledge.KnowledgeNotFound:
                pass
            else:
                if (
                    request["status"] in {"queued_for_hermes", "proposed"}
                    and _scope_status(request, item) != "current"
                ):
                    with conn.transaction():
                        conn.execute(
                            "UPDATE knowledge_edit_requests SET status = 'conflict', "
                            "updated_at = CURRENT_TIMESTAMP WHERE request_id = %s "
                            "AND status IN ('queued_for_hermes', 'proposed')",
                            (request_id,),
                        )
        raise
'''
    write(path, text)


def patch_information_owner() -> None:
    path = "mvp_vertical/information_projection.py"
    text = read(path)
    head, marker, tail = text.partition("def add_document_link")
    if not marker:
        raise SystemExit("add_document_link owner not found")
    tail = replace_once(
        tail,
        '''        if current["revision"] != expected_revision:
            raise StaleInformationProjectionWrite(f"stale Information projection revision: expected {expected_revision}, current {current['revision']}")
        conn.execute("""
''',
        '''        if current["revision"] != expected_revision:
            raise StaleInformationProjectionWrite(f"stale Information projection revision: expected {expected_revision}, current {current['revision']}")
        existing_link = conn.execute(
            "SELECT 1 FROM agency_information_document_links "
            "WHERE information_id = %s AND document_id = %s",
            (information_id, document_id),
        ).fetchone() is not None
        conn.execute("""
''',
        "detect existing Information Document link",
    )
    tail = replace_once(
        tail,
        '''        snapshot = get_projection(conn, information_id)
        _record_event(conn, information_id=information_id, event_type="document_link_added", actor=actor, actor_kind=actor_kind, expected_revision=expected_revision, resulting_revision=resulting_revision, idempotency_key=idempotency_key, payload_digest=digest, payload=payload, snapshot=snapshot)
        return snapshot
''',
        '''        snapshot = get_projection(conn, information_id)
        event_type = "document_link_updated" if existing_link else "document_link_added"
        mutation_result = {
            **snapshot,
            "document_link_operation": "updated" if existing_link else "created",
        }
        _record_event(conn, information_id=information_id, event_type=event_type, actor=actor, actor_kind=actor_kind, expected_revision=expected_revision, resulting_revision=resulting_revision, idempotency_key=idempotency_key, payload_digest=digest, payload=payload, snapshot=mutation_result)
        return mutation_result
''',
        "record Information Document upsert semantics",
    )
    write(path, head + marker + tail)


def patch_information_migration() -> None:
    path = "mvp_vertical/sql/013_information_card_projection.sql"
    text = read(path)
    text = replace_once(
        text,
        "event_type IN ('projection_metadata_updated', 'document_link_added', 'document_link_removed')",
        "event_type IN ('projection_metadata_updated', 'document_link_added', 'document_link_updated', 'document_link_removed')",
        "extend Information projection event vocabulary",
    )
    guard = '''

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'agency_information_projection_events_event_type_check'
           AND conrelid = 'agency_information_projection_events'::regclass
           AND pg_get_constraintdef(oid) LIKE '%document_link_updated%'
    ) THEN
        ALTER TABLE agency_information_projection_events
            DROP CONSTRAINT IF EXISTS agency_information_projection_events_event_type_check;
        ALTER TABLE agency_information_projection_events
            ADD CONSTRAINT agency_information_projection_events_event_type_check
            CHECK (event_type IN (
                'projection_metadata_updated',
                'document_link_added',
                'document_link_updated',
                'document_link_removed'
            ));
    END IF;
END;
$$;
'''
    needle = "\nCREATE OR REPLACE FUNCTION reject_agency_information_projection_event_mutation()"
    text = replace_once(text, needle, guard + needle, "guard Information event constraint")
    write(path, text)


def patch_source_schema_and_api() -> None:
    path = "mvp_vertical/sql/010_source_intake_admission.sql"
    text = read(path)
    text = replace_once(
        text,
        "    source_id TEXT PRIMARY KEY,\n",
        "    source_id TEXT PRIMARY KEY CHECK (source_id ~ '^[a-z0-9._-]+$'),\n",
        "Source id shape on fresh schema",
    )
    guard = '''

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'agency_sources_source_id_shape_check'
           AND conrelid = 'agency_sources'::regclass
    ) THEN
        ALTER TABLE agency_sources
            ADD CONSTRAINT agency_sources_source_id_shape_check
            CHECK (source_id ~ '^[a-z0-9._-]+$') NOT VALID;
    END IF;
END;
$$;
'''
    text = replace_once(
        text,
        "    UNIQUE (origin_system, origin_external_ref)\n);\n\nCREATE INDEX IF NOT EXISTS agency_sources_project_lookup",
        "    UNIQUE (origin_system, origin_external_ref)\n);" + guard
        + "\nCREATE INDEX IF NOT EXISTS agency_sources_project_lookup",
        "guard Source id constraint",
    )
    write(path, text)

    path = "mvp_vertical/source_intake_api.py"
    text = read(path)
    text = replace_once(
        text,
        "from . import source_intake\n",
        "from . import source_intake\nfrom .canonical_projections import project_source\n",
        "import Source projection",
    )
    text = replace_once(
        text,
        "    source_id: str = Field(min_length=1, max_length=200)\n",
        "    source_id: str = Field(min_length=1, max_length=200, pattern=r\"^[a-z0-9._-]+$\")\n",
        "validate Source id in API",
    )
    text = replace_once(
        text,
        '            "sources": sources,\n',
        '            "sources": sources,\n            "source_projections": [project_source(item) for item in sources],\n',
        "list canonical Source projections",
    )
    text = text.replace(
        '"source": source,',
        '"source": source, "source_projection": project_source(source),',
    )
    text = text.replace(
        '"source": source}',
        '"source": source, "source_projection": project_source(source)}',
    )
    write(path, text)


def patch_information_api() -> None:
    path = "mvp_vertical/information_projection_api.py"
    text = read(path)
    text = replace_once(
        text,
        "from fastapi import Depends, FastAPI, HTTPException, status\n",
        "from fastapi import Depends, FastAPI, HTTPException, Response, status\n",
        "import dynamic Information response",
    )
    text = replace_once(
        text,
        "from . import information_projection\n",
        "from . import information_projection\nfrom .canonical_projections import project_information\n",
        "import Information projection",
    )
    text = replace_once(
        text,
        '        return {"system_of_record": "postgres", **projection}\n',
        '        return {"system_of_record": "postgres", "information_projection": project_information(projection), **projection}\n',
        "single canonical Information projection",
    )
    text = replace_once(
        text,
        '            "information_projections": projections,\n',
        '            "information_projections": projections,\n            "canonical_information_projections": [project_information(item) for item in projections],\n',
        "list canonical Information projections",
    )
    text = text.replace(
        '            "approval_inferred": False,\n            **projection,',
        '            "approval_inferred": False,\n            "information_projection": project_information(projection),\n            **projection,',
    )
    text = replace_once(
        text,
        '''    def link_information_document(
        information_id: str,
        body: DocumentLinkBody,
        writer_kind: Literal["human"] = Depends(require_human_writer),
''',
        '''    def link_information_document(
        information_id: str,
        body: DocumentLinkBody,
        response: Response,
        writer_kind: Literal["human"] = Depends(require_human_writer),
''',
        "dynamic Information link status signature",
    )
    head, marker, tail = text.partition("    def link_information_document(")
    if not marker:
        raise SystemExit("Information link route not found")
    tail = replace_once(
        tail,
        "        )\n        return {\n",
        '''        )
        response.status_code = (
            status.HTTP_201_CREATED
            if projection.get("document_link_operation") == "created"
            else status.HTTP_200_OK
        )
        return {
''',
        "dynamic Information link status body",
    )
    write(path, head + marker + tail)


def patch_composition() -> None:
    path = "mvp_vertical/cockpit_composed.py"
    text = read(path)
    text = replace_once(
        text,
        "    execution_results,\n    information_projection,\n",
        "    execution_results,\n    entity_relations,\n    information_projection,\n",
        "import Entity relation owner",
    )
    text = replace_once(
        text,
        "from .execution_result_api import install_execution_result_routes\n",
        "from .execution_result_api import install_execution_result_routes\nfrom .entity_relation_api import install_entity_relation_routes\n",
        "import Entity relation routes",
    )
    text = replace_once(
        text,
        '        conn.execute(information_projection.MIGRATION.read_text(encoding="utf-8"))\n',
        '        conn.execute(information_projection.MIGRATION.read_text(encoding="utf-8"))\n        conn.execute(entity_relations.MIGRATION.read_text(encoding="utf-8"))\n',
        "initialize Entity relation schema",
    )
    text = replace_once(
        text,
        "    install_apu_write_routes(\n",
        '''    install_entity_relation_routes(
        app,
        with_connection=with_connection,
        require_read_key=require_read_key,
        require_editor_key=require_editor_key,
    )
    install_apu_write_routes(
''',
        "install Entity relation routes",
    )
    write(path, text)


def patch_tests() -> None:
    path = "tests/test_knowledge_edit_variants.py"
    text = read(path)
    text = replace_once(
        text,
        "    authority: dict | None = None,\n) -> tuple[str, str]:\n",
        "    authority: dict | None = None,\n    extra_payload: dict | None = None,\n) -> tuple[str, str]:\n",
        "extend Knowledge test helper",
    )
    text = replace_once(
        text,
        "    }\n    execution_results.store_execution_result(\n",
        "    }\n    payload.update(extra_payload or {})\n    execution_results.store_execution_result(\n",
        "inject Knowledge candidate extra fields",
    )
    text += '''


def test_projection_conflict_status_survives_inner_rollback(conn, tmp_path) -> None:
    card = _publish(conn, tmp_path)
    review = _request(conn, card, count=1)
    execution_id, result_ref = _store_variant_result(
        conn,
        review,
        label="A",
        replacement="Préparer soigneusement le support.",
    )
    markdown = knowledge.get_knowledge_markdown(conn, card["knowledge_id"])
    knowledge.revise_knowledge(
        conn,
        knowledge_id=card["knowledge_id"],
        markdown=markdown + "\n\nMise à jour concurrente.",
        expected_version=card["version"],
        actor="architecte",
        actor_kind="human",
        idempotency_key=_id("concurrent-revision"),
    )

    with pytest.raises(knowledge_edit_variants.KnowledgeEditVariantConflict):
        _project(conn, execution_id, result_ref)

    stored = knowledge_edit_variants.get_variant_review(
        conn, review["edit_request"]["request_id"]
    )
    assert stored["edit_request"]["status"] == "conflict"


def test_projection_rejects_unknown_candidate_fields(conn, tmp_path) -> None:
    card = _publish(conn, tmp_path)
    review = _request(conn, card, count=1)
    execution_id, result_ref = _store_variant_result(
        conn,
        review,
        label="A",
        replacement="Préparer soigneusement le support.",
        extra_payload={"review_status": "approved"},
    )
    with pytest.raises(
        knowledge_edit_variants.KnowledgeEditVariantError,
        match="unsupported fields",
    ):
        _project(conn, execution_id, result_ref)
'''
    write(path, text)

    path = "tests/test_information_projection.py"
    text = read(path)
    text += '''


def test_document_link_update_has_distinct_operation_and_event(conn) -> None:
    info = _information(conn)
    document_id = _document(conn, info["project_id"])
    created = information_projection.add_document_link(
        conn,
        information_id=info["information_id"],
        document_id=document_id,
        role="supporting",
        observed_version=1,
        observed_digest=None,
        expected_revision=0,
        actor="reviewer",
        actor_kind="human",
        idempotency_key=_id("link-create"),
    )
    assert created["document_link_operation"] == "created"

    updated = information_projection.add_document_link(
        conn,
        information_id=info["information_id"],
        document_id=document_id,
        role="primary",
        observed_version=2,
        observed_digest="sha256:updated",
        expected_revision=1,
        actor="reviewer",
        actor_kind="human",
        idempotency_key=_id("link-update"),
    )
    assert updated["document_link_operation"] == "updated"
    assert [
        row[0]
        for row in conn.execute(
            "SELECT event_type FROM agency_information_projection_events "
            "WHERE information_id = %s ORDER BY occurred_at, event_id",
            (info["information_id"],),
        ).fetchall()
    ] == ["document_link_added", "document_link_updated"]
'''
    write(path, text)

    path = "tests/test_entity_relations.py"
    text = read(path)
    text = replace_once(
        text,
        '    connection.execute("BEGIN")\n',
        '    connection.commit()\n    connection.execute("BEGIN")\n',
        "prepare Entity relation test transaction",
    )
    write(path, text)


def cleanup() -> None:
    for relative in (
        ".github/workflows/apply-a-b-relations-convergence.yml",
        ".github/workflows/run-a-b-relations-convergence-on-pr.yml",
        ".github/a-b-relations-patch.trigger",
        ".github/scripts/apply_a_b_relations_convergence.py",
    ):
        path = ROOT / relative
        if path.exists():
            path.unlink()


def main() -> None:
    rename_information_migration()
    patch_knowledge_projection()
    patch_information_owner()
    patch_information_migration()
    patch_source_schema_and_api()
    patch_information_api()
    patch_composition()
    patch_tests()
    cleanup()


if __name__ == "__main__":
    main()
