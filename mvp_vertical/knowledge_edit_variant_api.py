"""Bounded mobile review routes for Knowledge edit proposal variants."""

from __future__ import annotations

from typing import Callable, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from . import knowledge, knowledge_edit_variants


class VariantEditRequestBody(BaseModel):
    request_id: str = Field(min_length=3, max_length=200)
    instruction_kind: Literal["rewrite", "expand", "simplify", "verify", "move_to_lot"]
    instruction: str = Field(min_length=1, max_length=10_000)
    base_version: int = Field(ge=1)
    selection_start: int = Field(ge=0)
    selection_end: int = Field(ge=0)
    selected_text: str
    requested_by: str = Field(min_length=1, max_length=500)
    requested_variant_count: Literal[1, 2] = 1
    idempotency_key: str = Field(min_length=8, max_length=200)


class VariantProposalBody(BaseModel):
    replacement_markdown: str = Field(min_length=1, max_length=500_000)
    proposed_by: str = Field(min_length=1, max_length=500)
    idempotency_key: str = Field(min_length=8, max_length=200)


class VariantSelectionBody(BaseModel):
    variant_id: str = Field(min_length=3, max_length=200)
    idempotency_key: str = Field(min_length=8, max_length=200)


class VariantRejectionBody(BaseModel):
    reason: str = Field(min_length=1, max_length=10_000)
    idempotency_key: str = Field(min_length=8, max_length=200)


class ApplySelectedVariantBody(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)


def install_knowledge_edit_variant_routes(
    app: FastAPI,
    *,
    with_connection: Callable,
    require_editor_key: Callable,
    require_hermes_key: Callable,
    require_human_actor: Callable,
) -> None:
    def operation(call):
        try:
            return with_connection(call)
        except knowledge.KnowledgeNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (knowledge.StaleKnowledgeWrite, knowledge.IdempotencyConflict) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except knowledge.KnowledgeError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/knowledge/{knowledge_id}/variant-edit-requests", status_code=202)
    def create_variant_edit_request(
        knowledge_id: str,
        body: VariantEditRequestBody,
        _authorized: None = Depends(require_editor_key),
    ) -> dict:
        review = operation(
            lambda conn: knowledge_edit_variants.create_variant_request(
                conn,
                knowledge_id=knowledge_id,
                **body.model_dump(),
            )
        )
        return {
            "effect": "knowledge_edit_request_queued",
            "knowledge_mutated": False,
            "execution_authorized": False,
            "task_authorized": False,
            "evidence_admitted": False,
            **review,
        }

    @app.put("/edit-requests/{request_id}/variants/{variant_label}")
    def submit_edit_variant(
        request_id: str,
        variant_label: Literal["A", "B"],
        body: VariantProposalBody,
        _authorized: None = Depends(require_hermes_key),
    ) -> dict:
        review = operation(
            lambda conn: knowledge_edit_variants.submit_variant(
                conn,
                request_id=request_id,
                variant_label=variant_label,
                **body.model_dump(),
            )
        )
        return {
            "effect": "knowledge_edit_variant_proposed",
            "knowledge_mutated": False,
            "human_selection_required": True,
            "evidence_admitted": False,
            **review,
        }

    @app.get("/knowledge/{knowledge_id}/edit-reviews")
    def list_edit_reviews(
        knowledge_id: str,
        status: Literal[
            "queued_for_hermes", "proposed", "applied", "conflict", "rejected"
        ] | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        _authorized: None = Depends(require_editor_key),
    ) -> dict:
        reviews = operation(
            lambda conn: knowledge_edit_variants.list_variant_reviews(
                conn,
                knowledge_id=knowledge_id,
                status=status,
                limit=limit,
            )
        )
        return {
            "knowledge_id": knowledge_id,
            "edit_reviews": reviews,
            "variant_selected_is_edit_applied": False,
            "proposal_is_evidence": False,
        }

    @app.get("/edit-requests/{request_id}/review")
    def get_edit_review(
        request_id: str,
        _authorized: None = Depends(require_editor_key),
    ) -> dict:
        return operation(
            lambda conn: knowledge_edit_variants.get_variant_review(conn, request_id)
        )

    @app.post("/edit-requests/{request_id}/select-variant")
    def select_edit_variant(
        request_id: str,
        body: VariantSelectionBody,
        actor: str = Depends(require_human_actor),
        _authorized: None = Depends(require_editor_key),
    ) -> dict:
        review = operation(
            lambda conn: knowledge_edit_variants.select_variant(
                conn,
                request_id=request_id,
                variant_id=body.variant_id,
                actor=actor,
                idempotency_key=body.idempotency_key,
            )
        )
        return {
            "effect": "knowledge_edit_variant_selected",
            "knowledge_mutated": False,
            "edit_applied": False,
            "task_authorized": False,
            "evidence_admitted": False,
            **review,
        }

    @app.post("/edit-requests/{request_id}/reject")
    def reject_edit_request(
        request_id: str,
        body: VariantRejectionBody,
        actor: str = Depends(require_human_actor),
        _authorized: None = Depends(require_editor_key),
    ) -> dict:
        review = operation(
            lambda conn: knowledge_edit_variants.reject_request(
                conn,
                request_id=request_id,
                actor=actor,
                reason=body.reason,
                idempotency_key=body.idempotency_key,
            )
        )
        return {
            "effect": "knowledge_edit_request_rejected",
            "knowledge_mutated": False,
            "task_authorized": False,
            "evidence_admitted": False,
            **review,
        }

    @app.post("/edit-requests/{request_id}/apply-selected")
    def apply_selected_edit_variant(
        request_id: str,
        body: ApplySelectedVariantBody,
        actor: str = Depends(require_human_actor),
        _authorized: None = Depends(require_editor_key),
    ) -> dict:
        applied = operation(
            lambda conn: knowledge_edit_variants.apply_selected_variant(
                conn,
                request_id=request_id,
                actor=actor,
                idempotency_key=body.idempotency_key,
            )
        )
        return {
            "effect": "selected_knowledge_edit_variant_applied",
            "variant_selection_was_authorization": False,
            "review_status_promoted": False,
            "evidence_admitted": False,
            **applied,
        }
