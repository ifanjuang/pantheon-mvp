"""Read-only directory projections for native Agency Data.

People, Organizations and project participations remain PostgreSQL-owned records.
This module exposes normalized reads only; mutation policy is intentionally kept
separate until actor/gate rules are defined for those record families.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from . import agency_data


class AgencyDirectoryError(ValueError):
    pass


class PersonNotFound(AgencyDirectoryError):
    pass


class OrganizationNotFound(AgencyDirectoryError):
    pass


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _bounded_limit(limit: int) -> int:
    if limit < 1 or limit > 500:
        raise AgencyDirectoryError("directory limit must be between 1 and 500")
    return limit


def list_people(
    conn: psycopg.Connection,
    *,
    query: str | None = None,
    limit: int = 100,
) -> list[dict]:
    _bounded_limit(limit)
    params: list[Any] = []
    where = ""
    if query and query.strip():
        needle = f"%{query.strip()}%"
        where = "WHERE display_name ILIKE %s OR email ILIKE %s OR phone ILIKE %s"
        params.extend([needle, needle, needle])
    params.append(limit)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT *
              FROM agency_people
              {where}
             ORDER BY lower(display_name), person_id
             LIMIT %s
            """,
            params,
        )
        rows = cur.fetchall()
    return [_jsonable(dict(row)) for row in rows]


def get_person(conn: psycopg.Connection, person_id: str) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM agency_people WHERE person_id = %s", (person_id,))
        row = cur.fetchone()
    if row is None:
        raise PersonNotFound(f"unknown Agency Person: {person_id}")
    return _jsonable(dict(row))


def list_organizations(
    conn: psycopg.Connection,
    *,
    query: str | None = None,
    limit: int = 100,
) -> list[dict]:
    _bounded_limit(limit)
    params: list[Any] = []
    where = ""
    if query and query.strip():
        needle = f"%{query.strip()}%"
        where = "WHERE name ILIKE %s OR email ILIKE %s OR phone ILIKE %s OR siret ILIKE %s"
        params.extend([needle, needle, needle, needle])
    params.append(limit)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT *
              FROM agency_organizations
              {where}
             ORDER BY lower(name), organization_id
             LIMIT %s
            """,
            params,
        )
        rows = cur.fetchall()
    return [_jsonable(dict(row)) for row in rows]


def get_organization(conn: psycopg.Connection, organization_id: str) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT * FROM agency_organizations WHERE organization_id = %s",
            (organization_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise OrganizationNotFound(f"unknown Agency Organization: {organization_id}")
    return _jsonable(dict(row))


def list_project_participations(conn: psycopg.Connection, project_id: str) -> list[dict]:
    # Reuse the project-owned relation query so project existence and relation
    # semantics stay in one adapter rather than drifting across modules.
    try:
        return agency_data.list_project_participations(conn, project_id)
    except agency_data.ProjectNotFound as exc:
        raise AgencyDirectoryError(str(exc)) from exc
