"""Read-only HTTP surface for resolved Category collections."""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, FastAPI, HTTPException

from . import (
    agency_classification,
    category_collection_read,
    information_projection,
    knowledge,
    project_documents,
    work_issues,
)


def install_category_collection_read_routes(
    app: FastAPI,
    *,
    with_connection: Callable,
    require_read_key: Callable,
) -> None:
    def operation(fn):
        try:
            return with_connection(fn)
        except agency_classification.CategoryNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except category_collection_read.CategoryCollectionIntegrityError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (
            category_collection_read.CategoryCollectionReadError,
            agency_classification.AgencyClassificationError,
            information_projection.InformationProjectionError,
            knowledge.KnowledgeError,
            project_documents.ProjectDocumentError,
            work_issues.WorkIssueError,
        ) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/agency/categories/{category_id}/resolved-collection")
    def get_resolved_category_collection(
        category_id: str,
        _authorized: None = Depends(require_read_key),
    ) -> dict:
        return operation(
            lambda conn: category_collection_read.get_resolved_category_collection(
                conn,
                category_id,
            )
        )
