"""Cards-first cockpit composition over the bounded project APIs.

The shell exposes projections only. It does not own object status, approval,
execution, evidence, memory promotion or external action.
"""

from __future__ import annotations

import hmac
import os
from pathlib import Path
from typing import Callable, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import effect_preview, store, work_issue_read, work_issues
from .cockpit_api import create_app

COCKPIT = Path(__file__).resolve().parent / "cockpit"


class EffectPreviewBody(BaseModel):
    information: str = Field(min_length=3, max_length=4000)
    explicit_object_refs: list[str] = Field(default_factory=list, max_length=10)
    effect_hint: Literal["CREATE", "UPDATE", "SUPERSEDE", "CONFLICT"] | None = None
    max_proposals: int = Field(default=5, ge=1, le=10)


def connect_cockpit():
    """Open the shared store and ensure the existing Work Issue slice exists."""
    conn = store.connect()
    conn.execute(work_issues.MIGRATION.read_text(encoding="utf-8"))
    conn.commit()
    return conn


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        return ""
    return authorization.removeprefix("Bearer ").strip()


def create_cockpit_app(
    *,
    connect_fn: Callable = connect_cockpit,
    document_root: str | Path | None = None,
    api_key: str | None = None,
    editor_api_key: str | None = None,
    hermes_api_key: str | None = None,
    public_url: str | None = None,
) -> FastAPI:
    """Compose the existing bounded API with the cards-first static shell."""
    app = create_app(
        connect_fn=connect_fn,
        document_root=document_root,
        api_key=api_key,
        editor_api_key=editor_api_key,
        hermes_api_key=hermes_api_key,
        public_url=public_url,
    )

    def require_read_key(authorization: str | None = Header(default=None)) -> None:
        supplied = _bearer_token(authorization)
        expected = [key for key in (app.state.api_key, app.state.editor_api_key) if key]
        if not expected:
            raise HTTPException(status_code=503, detail="read API key is not configured")
        if not any(hmac.compare_digest(supplied, key) for key in expected):
            raise HTTPException(status_code=401, detail="invalid read API key")

    def with_connection(operation):
        conn = app.state.connect_fn()
        try:
            return operation(conn)
        finally:
            conn.close()

    @app.get("/v1/projects/{parent_project_id}/work-issues")
    def project_work_issues(
        parent_project_id: str,
        include_terminal: bool = True,
        limit: int = 100,
        _authorized: None = Depends(require_read_key),
    ) -> dict:
        """List Work Issues whose exact `case_ref` matches the opened project."""
        try:
            projections = with_connection(
                lambda conn: work_issue_read.list_issue_projections(
                    conn,
                    parent_project_id,
                    include_terminal=include_terminal,
                    limit=limit,
                )
            )
        except work_issues.WorkIssueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "parent_project_id": parent_project_id,
            "scope_match": "exact_case_ref",
            "work_issues": projections,
        }

    @app.post("/v1/projects/{parent_project_id}/effects/preview")
    def preview_project_effects(
        parent_project_id: str,
        body: EffectPreviewBody,
        _authorized: None = Depends(require_read_key),
    ) -> dict:
        """Propose deterministic effects without persisting or applying them."""
        try:
            return with_connection(
                lambda conn: effect_preview.preview_project_effects(
                    conn,
                    parent_project_id=parent_project_id,
                    information=body.information,
                    explicit_object_refs=body.explicit_object_refs,
                    effect_hint=body.effect_hint,
                    max_proposals=body.max_proposals,
                )
            )
        except effect_preview.EffectPreviewError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    if COCKPIT.is_dir():
        app.mount("/cockpit", StaticFiles(directory=COCKPIT, html=True), name="cockpit")
    return app


app = create_cockpit_app()


def run() -> None:
    """Run the composed internal cockpit API with uvicorn."""
    import uvicorn

    uvicorn.run(
        "mvp_vertical.cockpit_shell:app",
        host=os.getenv("MVP_COCKPIT_HOST", "127.0.0.1"),
        port=int(os.getenv("MVP_COCKPIT_PORT", "8081")),
        reload=False,
    )


if __name__ == "__main__":
    run()
