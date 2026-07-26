from __future__ import annotations

import uuid

import pytest

from mvp_vertical import agency_data, agency_schema


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def test_project_schema_declares_registry_without_granting_authority() -> None:
    schema = agency_schema.get_project_schema()
    assert schema["entity_type"] == "project"
    assert schema["version"] == 1
    assert schema["authority"]["system_of_record"] == "postgres"
    assert schema["authority"]["field_posture_is_authorization"] is False

    fields = {field["key"]: field for field in schema["fields"]}
    assert fields["budget"]["storage"] == "attributes"
    assert fields["budget"]["type"] == "number"
    assert fields["budget"]["hermes_mode"] == "candidate"
    assert fields["revision"]["storage"] == "system"
    assert fields["revision"]["hermes_mode"] == "system"


def test_project_attributes_are_normalized_by_registry() -> None:
    normalized = agency_schema.normalize_project_attributes(
        {
            "budget": 600000,
            "surface_terrain": 2712.0,
            "parcelles": ["AD-85", " AD-85 ", "AD-86"],
            "permit_date": "2026-07-26",
            "plu_zone": " UDb ",
        }
    )
    assert normalized == {
        "budget": 600000,
        "surface_terrain": 2712.0,
        "parcelles": ["AD-85", "AD-86"],
        "permit_date": "2026-07-26",
        "plu_zone": "UDb",
    }


def test_project_attributes_reject_unknown_or_wrong_types() -> None:
    with pytest.raises(agency_schema.AgencySchemaError, match="unsupported Project attribute"):
        agency_schema.normalize_project_attributes({"invented_field": "x"})
    with pytest.raises(agency_schema.AgencySchemaError, match="budget must be numeric"):
        agency_schema.normalize_project_attributes({"budget": "600000"})
    with pytest.raises(agency_schema.AgencySchemaError, match="permit_date must be an ISO date"):
        agency_schema.normalize_project_attributes({"permit_date": "26/07/2026"})


def test_project_attributes_round_trip_through_postgres_when_available() -> None:
    try:
        conn = agency_data.connect()
    except Exception as exc:  # pragma: no cover - local unit-only environment
        pytest.skip(f"PostgreSQL unreachable: {exc}")

    project_id = _id("project-schema")
    try:
        created = agency_data.create_project(
            conn,
            project_id=project_id,
            code=_id("SCHEMA")[:24],
            display_name="Projet schema-driven",
            actor="human",
            actor_kind="human",
            idempotency_key=_id("create"),
            attributes={"budget": 350000, "plu_zone": "UC0"},
        )
        assert created["attributes"] == {"budget": 350000, "plu_zone": "UC0"}

        updated = agency_data.update_project(
            conn,
            project_id=project_id,
            changes={"attributes": {"budget": 375000, "erp_type": "5e catégorie"}},
            actor="human",
            actor_kind="human",
            expected_revision=created["revision"],
            idempotency_key=_id("update"),
        )
        assert updated["revision"] == created["revision"] + 1
        assert updated["attributes"] == {"budget": 375000, "erp_type": "5e catégorie"}
    finally:
        # Agency events are deliberately RESTRICT-linked and append-only in normal
        # operation. Test cleanup removes the fixture history explicitly before
        # deleting its fixture Project.
        conn.execute("DELETE FROM agency_project_events WHERE project_id = %s", (project_id,))
        conn.execute("DELETE FROM agency_projects WHERE project_id = %s", (project_id,))
        conn.commit()
        conn.close()


def test_project_schema_is_exposed_by_agency_api_and_packaged() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    api = (root / "mvp_vertical" / "agency_data_api.py").read_text(encoding="utf-8")
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert '@app.get("/v1/agency/schema/project")' in api
    assert "attributes: dict[str, Any]" in api
    assert '"agency_schema/*.json"' in pyproject
