"""API boundary for execution admission and external Hermes runtime callbacks.

The Cockpit may admit one exact submitted handoff. Hermes may then fetch that
admission by ID and report its own runtime start and normalized return. There is
deliberately no pending-work listing, scheduler, queue, dispatch endpoint or
provider routing.
"""

from __future__ import annotations

import hmac
from typing import Callable, Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from . import hermes_execution, hermes_runtime_return, work_issues


class ExecutionAdmissionBody(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=200)


class HermesRuntimeStartBody(BaseModel):
    run_id: str = Field(min_length=1, max_length=300)
    expected_issue_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=200)


class HermesNormalizedReturn(BaseModel):
    outcome: Literal["result_candidate", "partial", "failed", "capability_gap"]
    summary: str = Field(min_length=1, max_length=20_000)
    trace_refs: list[str] = Field(min_length=1, max_length=500)
    source_refs: list[str] = Field(default_factory=list, max_length=500)
    evidence_candidate_refs: list[str] = Field(default_factory=list, max_length=500)
    limitations: list[str] = Field(default_factory=list, max_length=200)
    open_questions: list[str] = Field(default_factory=list, max_length=200)


class HermesRuntimeReturnBody(BaseModel):
    normalized_return: HermesNormalizedReturn
    expected_issue_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=200)


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        return ""
    return authorization.removeprefix("Bearer ").strip()


def install_hermes_execution_routes(
    app: FastAPI,
    *,
    require_editor_key: Callable,
    require_human_actor: Callable,
    with_connection: Callable | None = None,
) -> None:
    def use_connection(operation):
        if with_connection is not None:
            return with_connection(operation)
        conn = app.state.connect_fn()
        try:
            return operation(conn)
        finally:
            conn.close()

    def require_hermes_key(authorization: str | None = Header(default=None)) -> None:
        expected = getattr(app.state, "hermes_api_key", "")
        if not expected:
            raise HTTPException(status_code=503, detail="Hermes API key is not configured")
        if not hmac.compare_digest(_bearer_token(authorization), expected):
            raise HTTPException(status_code=401, detail="invalid Hermes API key")

    def require_hermes_actor(
        x_pantheon_hermes_actor: str | None = Header(
            default=None, alias="X-Pantheon-Hermes-Actor"
        ),
    ) -> str:
        if not x_pantheon_hermes_actor or not x_pantheon_hermes_actor.strip():
            raise HTTPException(
                status_code=422,
                detail="X-Pantheon-Hermes-Actor is required for a runtime callback",
            )
        return x_pantheon_hermes_actor.strip()

    connect_fn = getattr(app.state, "connect_fn", None)
    if (
        getattr(connect_fn, "__module__", "") == "mvp_vertical.cockpit_shell"
        and getattr(connect_fn, "__name__", "") == "connect_cockpit"
    ):
        def initialize_execution_admission_schema() -> None:
            conn = connect_fn()
            try:
                conn.execute(hermes_execution.MIGRATION.read_text(encoding="utf-8"))
                conn.commit()
            finally:
                conn.close()

        app.add_event_handler("startup", initialize_execution_admission_schema)

    @app.post(
        "/v1/cockpit/hermes-handoffs/{handoff_id}/admissions",
        status_code=201,
    )
    def admit_hermes_handoff(
        handoff_id: str,
        body: ExecutionAdmissionBody,
        _authorized: None = Depends(require_editor_key),
        actor: str = Depends(require_human_actor),
    ) -> dict:
        try:
            return use_connection(
                lambda conn: hermes_execution.admit_handoff(
                    conn,
                    handoff_id=handoff_id,
                    actor=actor,
                    idempotency_key=body.idempotency_key,
                )
            )
        except hermes_execution.AdmissionNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except hermes_execution.AdmissionConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except hermes_execution.HermesExecutionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/hermes/execution-admissions/{admission_id}")
    def get_hermes_execution_envelope(
        admission_id: str,
        _authorized: None = Depends(require_hermes_key),
    ) -> dict:
        try:
            return use_connection(
                lambda conn: hermes_execution.get_execution_envelope(conn, admission_id)
            )
        except hermes_execution.AdmissionNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except hermes_execution.AdmissionConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post(
        "/v1/hermes/execution-admissions/{admission_id}/runs/start",
        status_code=201,
    )
    def record_hermes_runtime_start(
        admission_id: str,
        body: HermesRuntimeStartBody,
        _authorized: None = Depends(require_hermes_key),
        actor: str = Depends(require_hermes_actor),
    ) -> dict:
        try:
            return use_connection(
                lambda conn: hermes_execution.record_external_runtime_start(
                    conn,
                    admission_id=admission_id,
                    run_id=body.run_id,
                    actor=actor,
                    expected_issue_version=body.expected_issue_version,
                    idempotency_key=body.idempotency_key,
                )
            )
        except hermes_execution.AdmissionNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (hermes_execution.AdmissionConflict, hermes_execution.RuntimeStartConflict) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except work_issues.StaleWrite as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (hermes_execution.HermesExecutionError, work_issues.WorkIssueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post(
        "/v1/hermes/execution-admissions/{admission_id}/runs/{run_id}/return",
        status_code=200,
    )
    def record_hermes_runtime_return(
        admission_id: str,
        run_id: str,
        body: HermesRuntimeReturnBody,
        _authorized: None = Depends(require_hermes_key),
        actor: str = Depends(require_hermes_actor),
    ) -> dict:
        try:
            return use_connection(
                lambda conn: hermes_runtime_return.record_external_runtime_return(
                    conn,
                    admission_id=admission_id,
                    run_id=run_id,
                    normalized_return=body.normalized_return.model_dump(),
                    actor=actor,
                    expected_issue_version=body.expected_issue_version,
                    idempotency_key=body.idempotency_key,
                )
            )
        except hermes_runtime_return.HermesRuntimeReturnConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except hermes_runtime_return.HermesRuntimeReturnError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
