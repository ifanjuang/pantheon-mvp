from __future__ import annotations

import json
from pathlib import Path


FIXTURES = Path(__file__).parent / "fixtures" / "ifja"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_f01_is_synthetic_and_exercises_existing_v2_families() -> None:
    fixture = _load("f01_maison_neuve.json")

    assert fixture["fixture_id"] == "F01"
    assert fixture["synthetic"] is True
    assert fixture["project"]["project_id"] == "fixture-project-f01"
    assert fixture["information"]
    assert fixture["contacts"]
    assert fixture["work"]
    assert fixture["decisions"]


def test_f01_consequential_project_values_are_claims_not_attributes() -> None:
    fixture = _load("f01_maison_neuve.json")
    attributes = fixture["project"]["attributes"]
    claim_types = {claim["claim_type"] for claim in fixture["project_claims"]}

    assert not ({"surface_projet", "surface_terrain", "zone_plu", "budget", "parcelles", "permit_number"} & attributes.keys())
    assert {"surface_projet", "surface_terrain", "zone_plu", "budget", "parcelle", "permit_number"} <= claim_types


def test_f01_source_backed_claims_resolve_to_information() -> None:
    fixture = _load("f01_maison_neuve.json")
    information_keys = {item["key"] for item in fixture["information"]}

    for claim in fixture["project_claims"]:
        if claim["status"] == "source_backed":
            assert claim["backing_information_key"] in information_keys


def test_f01_asserted_claim_can_exist_without_backing() -> None:
    fixture = _load("f01_maison_neuve.json")
    budget = next(claim for claim in fixture["project_claims"] if claim["claim_type"] == "budget")

    assert budget["status"] == "asserted"
    assert budget["backing_information_key"] is None


def test_f01_keeps_type_tags_subject_tags_status_and_limits_distinct() -> None:
    fixture = _load("f01_maison_neuve.json")

    for information in fixture["information"]:
        assert isinstance(information["type_tags"], list)
        assert isinstance(information["subject_tags"], list)
        assert isinstance(information["limits"], list)
        assert information["status"] in {"draft", "in_progress", "acted"}
        assert not (set(information["type_tags"]) & set(information["limits"]))
        assert not (set(information["subject_tags"]) & set(information["limits"]))
