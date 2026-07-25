"""Preview-only API for the Cockpit Hermes dock.

The route prepares exact Task Contract and Context Pack candidates. It performs
no runtime dispatch and persists no Work Issue.
"""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import hermes_handoff_preview


class EntityRefBody(BaseModel):
    entity_id: str = Field(min_length=1, max_length=500)
    entity_type: str = Field(min_length=1, max_length=200)


class CardContextEnvelopeBody(BaseModel):
    root_entity: EntityRefBody
    descendants: list[EntityRefBody] = Field(default_factory=list, max_length=250)
    source_refs: list[str] = Field(default_factory=list, max_length=500)
    explicit_additions: list[EntityRefBody] = Field(default_factory=list, max_length=250)
    explicit_exclusions: list[EntityRefBody] = Field(default_factory=list, max_length=250)
    scope_widened_implicitly: bool = False


class HermesHandoffPreviewBody(BaseModel):
    question: str = Field(min_length=3, max_length=8_000)
    card_context_envelope: CardContextEnvelopeBody
    selected_context: list[EntityRefBody] = Field(default_factory=list, max_length=250)


def install_hermes_handoff_preview_routes(
    app: FastAPI,
    *,
    require_read_key: Callable,
) -> None:
    @app.post("/v1/cockpit/hermes-handoffs/preview")
    def preview_hermes_handoff(
        body: HermesHandoffPreviewBody,
        _authorized: None = Depends(require_read_key),
    ) -> dict:
        if body.card_context_envelope.scope_widened_implicitly:
            raise HTTPException(
                status_code=422,
                detail="Card Context Envelope may not widen scope implicitly",
            )
        try:
            return hermes_handoff_preview.build_preview(
                question=body.question,
                card_context_envelope=body.card_context_envelope.model_dump(),
                selected_context=[item.model_dump() for item in body.selected_context],
            )
        except hermes_handoff_preview.HandoffPreviewError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
