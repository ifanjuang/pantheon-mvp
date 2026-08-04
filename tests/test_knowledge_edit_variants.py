from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from mvp_vertical import knowledge, knowledge_edit_variants, store
from mvp_vertical.contract import TaskContract


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


@pytest.fixture
def conn():
    try:
        connection = store.connect()
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"PostgreSQL/pgvector unreachable: {exc}")
    knowledge_edit_variants.ensure_schema(connection)
    yield connection
    connection.close()


def _publish(conn, tmp_path: Path) -> dict:
    suffix = uuid.uuid4().hex
    dossier = f"variant-{suffix}"
    source_ref = (
        "Projects/MAISON-A/30_DCE/"
        f"MAISON-A_A1_DCE_IFJ_CCTP_LOT-06-{suffix}_2026-08-04.md"
    )
    path = tmp_path / source_ref
    path.parent.mkdir(parents=True)
    path.write_text("# Façades\n\nPréparer le support existant.", encoding="utf-8")
    raw = {
        "object_type": "task_contract",
        "object_id": f"tc.{suffix}",
        "contract_id": f"tc.{suffix}",
        "scope": {
            "dossier": dossier,
            "parent_project_id": "project-maison-a",
            "declared_sources": [{"source_ref": source_ref}],
        },
    }
    contract = TaskContract(
        raw=raw,
        path=tmp_path / "task_contract.yaml",
        dossier=dossier,
        sources=(source_ref,),
    )
    assert store.ingest(conn, contract, tmp_path, ingestion_id=f"ingest-{suffix}") == 1
    document = store.get_document_card(conn, dossier, source_ref)
    compilation_id = document["structured_extraction"]["compilation_id"]
    return knowledge.publish_knowledge(
        conn,
        knowledge_id=f"knowledge.techniques.{suffix}",
        document_id=document["document_id"],
        title="Reprise des façades",
        family="techniques",
        markdown="# Reprise des façades\n\nPréparer le support existant.",
        source_chunk_refs=[f"chunk.{compilation_id}.0000"],
        created_by="hermes-test",
        actor_kind="hermes",
        idempotency_key=_id("publish"),
    )


def _request(conn, card: dict, *, count: int = 2) -> dict:
    markdown = knowledge.get_knowledge_markdown(conn, card["knowledge_id"])
    selected = "Préparer le support existant."
    start = markdown.index(selected)
    return knowledge_edit_variants.create_variant_request(
        conn,
        request_id=_id("edit"),
        knowledge_id=card["knowledge_id"],
        instruction_kind="rewrite",
        instruction="Proposer des formulations alternatives.",
        base_version=card["version"],
        selection_start=start,
        selection_end=start + len(selected),
        selected_text=selected,
        requested_by="architecte",
        requested_variant_count=count,
        idempotency_key=_id("request"),
    )


def test_ab_variants_share_one_scope_and_selection_does_not_apply(conn, tmp_path) -> None:
    card = _publish(conn, tmp_path)
    review = _request(conn, card, count=2)
    request_id = review["edit_request"]["request_id"]
    original = knowledge.get_knowledge_markdown(conn, card["knowledge_id"])

    first_key = _id("variant-a")
    first = knowledge_edit_variants.submit_variant(
        conn,
        request_id=request_id,
        variant_label="A",
        replacement_markdown="Nettoyer et préparer le support existant.",
        proposed_by="hermes",
        idempotency_key=first_key,
    )
    assert first["edit_request"]["status"] == "queued_for_hermes"
    assert len(first["variants"]) == 1
    assert knowledge_edit_variants.submit_variant(
        conn,
        request_id=request_id,
        variant_label="A",
        replacement_markdown="Nettoyer et préparer le support existant.",
        proposed_by="hermes",
        idempotency_key=first_key,
    )["variants"][0]["variant_label"] == "A"

    proposed = knowledge_edit_variants.submit_variant(
        conn,
        request_id=request_id,
        variant_label="B",
        replacement_markdown="Purger les parties non adhérentes, dépoussiérer puis appliquer le primaire.",
        proposed_by="hermes",
        idempotency_key=_id("variant-b"),
    )
    assert proposed["edit_request"]["status"] == "proposed"
    assert proposed["edit_request"]["requested_variant_count"] == 2
    assert [variant["variant_label"] for variant in proposed["variants"]] == ["A", "B"]
    assert all(variant["diff"] for variant in proposed["variants"])
    assert {variant["request_id"] for variant in proposed["variants"]} == {request_id}

    variant_b = next(variant for variant in proposed["variants"] if variant["variant_label"] == "B")
    selected = knowledge_edit_variants.select_variant(
        conn,
        request_id=request_id,
        variant_id=variant_b["variant_id"],
        actor="architecte",
        idempotency_key=_id("select"),
    )
    assert selected["edit_request"]["selected_variant_id"] == variant_b["variant_id"]
    assert selected["variant_selected_is_edit_applied"] is False
    assert knowledge.get_knowledge_markdown(conn, card["knowledge_id"]) == original
    assert knowledge.get_knowledge_card(conn, card["knowledge_id"])["version"] == 1

    applied = knowledge_edit_variants.apply_selected_variant(
        conn,
        request_id=request_id,
        actor="architecte",
        idempotency_key=_id("apply"),
    )
    assert applied["knowledge"]["version"] == 2
    assert applied["review"]["edit_request"]["status"] == "applied"
    assert "Purger les parties" in knowledge.get_knowledge_markdown(conn, card["knowledge_id"])
    event_types = [event["event_type"] for event in applied["review"]["review_events"]]
    assert event_types == [
        "variant_proposed",
        "variant_proposed",
        "variant_selected",
        "variant_applied",
    ]


def test_variant_selection_requires_complete_proposal_and_rejection_is_non_mutating(conn, tmp_path) -> None:
    card = _publish(conn, tmp_path)
    review = _request(conn, card, count=1)
    request_id = review["edit_request"]["request_id"]
    original = knowledge.get_knowledge_markdown(conn, card["knowledge_id"])

    with pytest.raises(knowledge_edit_variants.KnowledgeEditVariantConflict):
        knowledge_edit_variants.select_variant(
            conn,
            request_id=request_id,
            variant_id="missing",
            actor="architecte",
            idempotency_key=_id("select"),
        )

    proposed = knowledge_edit_variants.submit_variant(
        conn,
        request_id=request_id,
        variant_label="A",
        replacement_markdown="Préparer méthodiquement le support existant.",
        proposed_by="hermes",
        idempotency_key=_id("variant"),
    )
    rejected = knowledge_edit_variants.reject_request(
        conn,
        request_id=request_id,
        actor="architecte",
        reason="Formulation non retenue.",
        idempotency_key=_id("reject"),
    )
    assert rejected["edit_request"]["status"] == "rejected"
    assert knowledge.get_knowledge_markdown(conn, card["knowledge_id"]) == original
    with pytest.raises(knowledge_edit_variants.KnowledgeEditVariantConflict):
        knowledge_edit_variants.select_variant(
            conn,
            request_id=request_id,
            variant_id=proposed["variants"][0]["variant_id"],
            actor="architecte",
            idempotency_key=_id("select-after-reject"),
        )


def test_review_events_are_append_only(conn, tmp_path) -> None:
    card = _publish(conn, tmp_path)
    review = _request(conn, card, count=1)
    request_id = review["edit_request"]["request_id"]
    proposed = knowledge_edit_variants.submit_variant(
        conn,
        request_id=request_id,
        variant_label="A",
        replacement_markdown="Préparer soigneusement le support existant.",
        proposed_by="hermes",
        idempotency_key=_id("variant"),
    )
    event_id = proposed["review_events"][0]["event_id"]
    with pytest.raises(Exception, match="append-only"):
        conn.execute(
            "UPDATE knowledge_edit_review_events SET actor = 'x' WHERE event_id = %s",
            (event_id,),
        )
    conn.rollback()
