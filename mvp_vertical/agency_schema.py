"""Declarative Agency Data schema loader and bounded attribute validation.

The registry describes business fields and named projections. It is not an
authorization engine: mutation routes and Pantheon governance remain authoritative.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

SCHEMA_ROOT = Path(__file__).resolve().parent / "agency_schema"
PROJECT_SCHEMA_PATH = SCHEMA_ROOT / "project.json"
DEFAULT_PROJECT_VIEW = "cockpit_back"


class AgencySchemaError(ValueError):
    pass


@lru_cache(maxsize=1)
def _project_schema_cached() -> dict[str, Any]:
    try:
        raw = json.loads(PROJECT_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgencySchemaError(f"unable to load Project schema: {exc}") from exc

    if raw.get("entity_type") != "project":
        raise AgencySchemaError("Project schema must declare entity_type=project")
    if not isinstance(raw.get("version"), int) or raw["version"] < 1:
        raise AgencySchemaError("Project schema version must be a positive integer")
    fields = raw.get("fields")
    if not isinstance(fields, list) or not fields:
        raise AgencySchemaError("Project schema must declare fields")

    seen: set[str] = set()
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            raise AgencySchemaError(f"Project schema field {index + 1} must be an object")
        key = str(field.get("key") or "").strip()
        if not key:
            raise AgencySchemaError(f"Project schema field {index + 1} requires a key")
        if key in seen:
            raise AgencySchemaError(f"duplicate Project schema field: {key}")
        seen.add(key)
        if field.get("storage") not in {"core", "attributes", "system"}:
            raise AgencySchemaError(f"unsupported storage for Project field {key}")
        if field.get("hermes_mode") not in {"no", "candidate", "auto", "bounded", "system"}:
            raise AgencySchemaError(f"unsupported hermes_mode for Project field {key}")

    views = raw.get("views")
    if not isinstance(views, dict) or not views:
        raise AgencySchemaError("Project schema must declare named views")
    for view_name, view in views.items():
        if not isinstance(view_name, str) or not view_name.strip():
            raise AgencySchemaError("Project schema view names must be non-empty strings")
        if not isinstance(view, dict):
            raise AgencySchemaError(f"Project schema view {view_name} must be an object")
        view_fields = view.get("fields")
        if not isinstance(view_fields, list) or not view_fields:
            raise AgencySchemaError(f"Project schema view {view_name} must declare fields")
        view_seen: set[str] = set()
        for field_key in view_fields:
            if not isinstance(field_key, str) or not field_key.strip():
                raise AgencySchemaError(f"Project schema view {view_name} contains an invalid field key")
            if field_key not in seen:
                raise AgencySchemaError(
                    f"Project schema view {view_name} references unknown field {field_key}"
                )
            if field_key in view_seen:
                raise AgencySchemaError(
                    f"Project schema view {view_name} repeats field {field_key}"
                )
            view_seen.add(field_key)
    if DEFAULT_PROJECT_VIEW not in views:
        raise AgencySchemaError(f"Project schema must declare default view {DEFAULT_PROJECT_VIEW}")
    return raw


def get_project_registry() -> dict[str, Any]:
    """Return the complete Project registry, including every declared field and view."""
    return deepcopy(_project_schema_cached())


def get_project_schema(view_name: str | None = DEFAULT_PROJECT_VIEW) -> dict[str, Any]:
    """Return a named Project projection; pass None for the complete registry.

    Named views narrow and order exposed fields only. They do not change field
    mutability or grant authorization; those remain enforced by server routes and
    Pantheon gates.
    """
    schema = deepcopy(_project_schema_cached())
    if view_name is None:
        return schema

    name = str(view_name or "").strip()
    view = schema["views"].get(name)
    if view is None:
        raise AgencySchemaError(f"unknown Project schema view: {name}")

    by_key = {field["key"]: field for field in schema["fields"]}
    schema["fields"] = [by_key[key] for key in view["fields"]]
    schema["resolved_view"] = {
        "name": name,
        "purpose": view.get("purpose"),
        "field_count": len(view["fields"]),
        "authorization_inferred": False,
    }
    return schema


def get_project_view(view_name: str) -> dict[str, Any]:
    """Return one validated named view without changing the cached registry."""
    schema = _project_schema_cached()
    name = str(view_name or "").strip()
    view = schema["views"].get(name)
    if view is None:
        raise AgencySchemaError(f"unknown Project schema view: {name}")
    return deepcopy(view)


def project_record_for_view(record: dict[str, Any], view_name: str) -> dict[str, Any]:
    """Project one Project record through a declared view.

    Attribute-backed fields are flattened into the returned record so consumers do
    not need to know PostgreSQL storage layout. This is a projection helper only;
    it grants no read scope or mutation authority.
    """
    schema = get_project_schema(view_name)
    attributes = record.get("attributes") or {}
    if not isinstance(attributes, dict):
        attributes = {}

    projected: dict[str, Any] = {}
    for field in schema["fields"]:
        key = field["key"]
        if field.get("storage") == "attributes":
            projected[key] = attributes.get(key)
        else:
            projected[key] = record.get(key)
    return projected


def _attribute_fields() -> dict[str, dict[str, Any]]:
    return {
        field["key"]: field
        for field in _project_schema_cached()["fields"]
        if field.get("storage") == "attributes"
    }


def _normalize_date(value: Any, *, key: str) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if not isinstance(value, str):
        raise AgencySchemaError(f"Project attribute {key} must be an ISO date")
    text = value.strip()
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise AgencySchemaError(f"Project attribute {key} must be an ISO date") from exc


def _normalize_value(field: dict[str, Any], value: Any) -> Any:
    key = field["key"]
    if value is None:
        if field.get("nullable", False):
            return None
        raise AgencySchemaError(f"Project attribute {key} may not be null")

    field_type = field.get("type")
    if field_type in {"string", "enum"}:
        if not isinstance(value, str):
            raise AgencySchemaError(f"Project attribute {key} must be a string")
        text = value.strip()
        if field_type == "enum" and text not in set(field.get("values") or []):
            raise AgencySchemaError(
                f"Project attribute {key} must be one of: {', '.join(field.get('values') or [])}"
            )
        return text
    if field_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise AgencySchemaError(f"Project attribute {key} must be numeric")
        return value
    if field_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise AgencySchemaError(f"Project attribute {key} must be an integer")
        return value
    if field_type == "boolean":
        if not isinstance(value, bool):
            raise AgencySchemaError(f"Project attribute {key} must be boolean")
        return value
    if field_type == "string_list":
        if not isinstance(value, list):
            raise AgencySchemaError(f"Project attribute {key} must be a list")
        output: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                raise AgencySchemaError(f"Project attribute {key} must contain strings only")
            text = item.strip()
            if not text or text.casefold() in seen:
                continue
            seen.add(text.casefold())
            output.append(text)
        return output
    if field_type == "date":
        return _normalize_date(value, key=key)

    raise AgencySchemaError(f"unsupported Project attribute type for {key}: {field_type}")


def normalize_project_attributes(attributes: dict[str, Any] | None) -> dict[str, Any]:
    """Validate only the extensible JSONB business attributes declared by the registry."""
    if attributes is None:
        return {}
    if not isinstance(attributes, dict):
        raise AgencySchemaError("Project attributes must be an object")

    fields = _attribute_fields()
    unknown = sorted(set(attributes) - set(fields))
    if unknown:
        raise AgencySchemaError(
            "unsupported Project attribute field(s): " + ", ".join(unknown)
        )

    return {
        key: _normalize_value(fields[key], value)
        for key, value in attributes.items()
    }
