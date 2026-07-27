from __future__ import annotations

import json
from pathlib import Path


FIXTURES = Path(__file__).parent / "fixtures" / "ifja"
FIXTURE_FILES = (
    "f01_maison_neuve.json",
    "f03_chantier_reserves.json",
    "f05_dce_marches.json",
)
CONSEQUENTIAL_PROJECT_FIELDS = {
    "surface_projet",
    "surface_terrain",
    "zone_plu",
    "budget",
    "parcelles",
    "permit_number",
    "permit_date",
    "reception_date",
    "montant_marche",
}


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _fixtures() -> list[dict]:
    return [_load(name) for name in FIXTURE_FILES]


def test_ifja_fixtures_are_synthetic_and_use_existing_v2_families() -> None:
    fixtures = _fixtures()

    assert {fixture["fixture_id"] for fixture in fixtures} == {"F01", "F03", "F05"}
    for fixture in fixtures:
        assert fixture["synthetic"] is True
        assert fixture["project"]["project_id"].startswith("fixture-project-")
        assert fixture["information"]
        assert fixture["contacts"]
        assert fixture["work"]
        assert fixture["decisions"]


def test_consequential_project_values_do_not_return_to_flexible_attributes() -> None:
    for fixture in _fixtures():
        attributes = fixture["project"].get("attributes") or {}
        assert not (CONSEQUENTIAL_PROJECT_FIELDS & set(attributes))


def test_source_backed_claims_resolve_to_information() -> None:
    for fixture in _fixtures():
        information_keys = {item["key"] for item in fixture["information"]}
        for claim in fixture.get("project_claims") or []:
            if claim["status"] == "source_backed":
                assert claim["backing_information_key"] in information_keys


def test_asserted_claims_are_allowed_without_fake_backing() -> None:
    asserted = [
        claim
        for fixture in _fixtures()
        for claim in fixture.get("project_claims") or []
        if claim["status"] == "asserted"
    ]

    assert asserted
    assert any(claim.get("backing_information_key") is None for claim in asserted)


def test_information_taxonomy_axes_remain_distinct() -> None:
    for fixture in _fixtures():
        for information in fixture["information"]:
            type_tags = set(information["type_tags"])
            subject_tags = set(information["subject_tags"])
            limits = set(information["limits"])
            assert information["status"] in {"draft", "in_progress", "acted"}
            assert not (type_tags & limits)
            assert not (subject_tags & limits)


def test_work_review_requires_separate_human_decision_in_consequential_cases() -> None:
    for fixture in (_load("f03_chantier_reserves.json"), _load("f05_dce_marches.json")):
        reviewed_work = {item["id"] for item in fixture["work"] if item.get("status") == "review"}
        decision_triggers = {item["trigger"] for item in fixture["decisions"] if item.get("human_required")}
        assert reviewed_work <= decision_triggers


def test_change_candidates_keep_revision_diff_provenance_and_idempotency() -> None:
    for fixture in (_load("f03_chantier_reserves.json"), _load("f05_dce_marches.json")):
        for candidate in fixture.get("change_candidates") or []:
            assert isinstance(candidate["base_revision"], int)
            assert candidate["changes"]
            assert candidate["provenance"]
            assert candidate["idempotency_key"]
            assert candidate["status"] == "pending_review"


def test_dce_document_types_do_not_collapse_into_subject_tags() -> None:
    fixture = _load("f05_dce_marches.json")
    type_vocab = {tag for item in fixture["information"] for tag in item["type_tags"]}
    subject_vocab = {tag for item in fixture["information"] for tag in item["subject_tags"]}

    assert {"DCE", "CCTP", "CCAP", "devis", "contrat"} <= type_vocab
    assert {"structure", "budget", "entreprise"} & subject_vocab
    assert not ({"CCTP", "CCAP"} & subject_vocab)
