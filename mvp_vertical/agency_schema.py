"""Declarative Agency Data schema loader and bounded attribute validation.

The registry describes business fields and presentation labels. It is not an
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
    return raw


def get_project_schema() -> dict[str, Any]:
    """Return a copy so callers cannot mutate the cached registry."""
    return deepcopy(_project_schema_cached())


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
