"""FastAPI route installer for native PostgreSQL Agency Data.

The HTTP surface is deliberately narrow: normalized reads plus explicit project
create/update commands with actor identity, idempotency and expected revision.
It is not a generic SQL endpoint and does not grant governance approval.
"""

from __future__ import annotations

from typing import Callable, Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import agency_data


class ProjectCreateBody(BaseModel):
    project_id: str = Field(min_length=1, max_length=200)
    code: str = Field(min_length=1, max_length=200)
    display_name: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=10_000)
    status: str | None = Field(default=None, max_length=200)
    phase: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=500)
    primary_client: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, max_length=50)
    idempotency_key: str = Field(min_length=8, max_length=200)


class ProjectUpdateBody(BaseModel):
    expected_revision: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=200)
    code: str | None = Field(default=None, min_length=1, max_length=200)
    display_name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10_000)
    status: str | None = Field(default=None, max_length=200)
    phase: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=500)
    primary_client: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = Field(default=None, max_length=50)


def install_agency_data_routes(
    app: FastAPI,
    *,
    with_connection: Callable,
    require_read_key: Callable,
    require_writer_kind: Callable,
    require_actor: Callable,
) -> None:
    def agency_operation(operation):
        try:
            return with_connection(operation)
        except agency_data.ProjectNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except agency_data.GovernanceGateRequired as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (agency_data.StaleProjectWrite, agency_data.IdempotencyConflict) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except agency_data.AgencyDataError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/agency/projects")
    def list_projects(
        q: str | None = None,
        limit: int = 100,
        _authorized: None = Depends(require_read_key),
    ) -> dict:
        projects = agency_operation(
            lambda conn: agency_data.list_projects(conn, query=q, limit=limit)
        )
        return {
            "system_of_record": "postgres",
            "scope_match": "agency_projects",
            "projects": projects,
        }

    @app.get("/v1/agency/projects/{project_id}")
    def get_project(
        project_id: str,
        _authorized: None = Depends(require_read_key),
    ) -> dict:
        project = agency_operation(lambda conn: agency_data.get_project(conn, project_id))
        return {"system_of_record": "postgres", "project": project}

    @app.get("/v1/agency/projects/{project_id}/participations")
    def get_project_participations(
        project_id: str,
        _authorized: None = Depends(require_read_key),
    ) -> dict:
        participations = agency_operation(
            lambda conn: agency_data.list_project_participations(conn, project_id)
        )
        return {
            "system_of_record": "postgres",
            "project_id": project_id,
            "participations": participations,
        }

    @app.post("/v1/agency/projects", status_code=201)
    def create_project(
        body: ProjectCreateBody,
        writer_kind: Literal["human", "hermes"] = Depends(require_writer_kind),
        actor: str = Depends(require_actor),
    ) -> dict:
        values = body.model_dump()
        idempotency_key = values.pop("idempotency_key")
        project = agency_operation(
            lambda conn: agency_data.create_project(
                conn,
                actor=actor,
                actor_kind=writer_kind,
                idempotency_key=idempotency_key,
                **values,
            )
        )
        return {
            "system_of_record": "postgres",
            "effect": "internal_agency_data_write",
            "approval_inferred": False,
            "project": project,
        }

    @app.patch("/v1/agency/projects/{project_id}")
    def update_project(
        project_id: str,
        body: ProjectUpdateBody,
        writer_kind: Literal["human", "hermes"] = Depends(require_writer_kind),
        actor: str = Depends(require_actor),
    ) -> dict:
        supplied = body.model_dump(exclude_unset=True)
        expected_revision = supplied.pop("expected_revision")
        idempotency_key = supplied.pop("idempotency_key")
        project = agency_operation(
            lambda conn: agency_data.update_project(
                conn,
                project_id=project_id,
                changes=supplied,
                actor=actor,
                actor_kind=writer_kind,
                expected_revision=expected_revision,
                idempotency_key=idempotency_key,
            )
        )
        return {
            "system_of_record": "postgres",
            "effect": "internal_agency_data_write",
            "approval_inferred": False,
            "project": project,
        }
