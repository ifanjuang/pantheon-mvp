"""Tests for the project-claim Agency Data seam.

The contract tests are hermetic (no database): they exercise the vendored
governance schema directly. The round-trip tests use PostgreSQL and skip when it
is unreachable, exactly like the Work Issue acceptance tests.
"""

from __future__ import annotations

import uuid

import pytest

from mvp_vertical import agency_claims


def _valid_claim(**overrides) -> dict:
    claim = {
        "claim_id": "claim.proj-01.zone-plu",
        "project_id": "project-01J8ZK2Q7X",
        "claim_type": "zone_plu",
        "value": "UB",
        "unit": None,
        "backing_card_ref": {
            "card_family": "knowledge",
            "card_id": "knowledge.plu.reglement-ub",
            "card_status": "published",
        },
        "provenance": {
            "source_kind": "document",
            "source_ref": "document.plu.2024",
            "asserted_by": "apu-adapter",
            "derivation_note": None,
        },
        "status": "source_backed",
        "observed_at": "2026-07-25T14:30:00Z",
        "revision": 1,
        "supersedes": None,
        "note": None,
        "governance_refs": list(agency_claims.GOVERNANCE_REFS),
    }
    claim.update(overrides)
    return claim


# --- hermetic contract tests (no database) --------------------------------


def test_valid_claim_passes_the_governed_contract() -> None:
    agency_claims.validate_claim(_valid_claim())


def test_claim_with_bad_id_pattern_is_rejected() -> None:
    with pytest.raises(agency_claims.ClaimContractViolation):
        agency_claims.validate_claim(_valid_claim(claim_id="Claim With Spaces"))


def test_claim_status_outside_the_lifecycle_is_rejected() -> None:
    # There is no "approved" status by construction: a claim is never opposable.
    with pytest.raises(agency_claims.ClaimContractViolation):
        agency_claims.validate_claim(_valid_claim(status="approved"))


def test_claim_without_backing_card_is_rejected() -> None:
    broken = _valid_claim()
    del broken["backing_card_ref"]
    with pytest.raises(agency_claims.ClaimContractViolation):
        agency_claims.validate_claim(broken)


def test_claim_with_unknown_card_family_is_rejected() -> None:
    with pytest.raises(agency_claims.ClaimContractViolation):
        agency_claims.validate_claim(
            _valid_claim(
                backing_card_ref={"card_family": "spreadsheet", "card_id": "x", "card_status": None}
            )
        )


def test_claim_with_extra_property_is_rejected() -> None:
    # additionalProperties: false — a claim may not smuggle an approval flag.
    with pytest.raises(agency_claims.ClaimContractViolation):
        agency_claims.validate_claim(_valid_claim(approved=True))


# --- PostgreSQL round-trip tests (skip when unreachable) ------------------


@pytest.fixture
def conn():
    try:
        connection = agency_claims.connect()
    except Exception as exc:  # pragma: no cover - local unit-only environment
        pytest.skip(f"PostgreSQL unreachable: {exc}")
    connection.execute("TRUNCATE agency.project_claim RESTART IDENTITY CASCADE")
    connection.commit()
    yield connection
    connection.close()


def _cid(prefix: str = "claim") -> str:
    return f"{prefix}.{uuid.uuid4().hex}"


def test_record_and_read_round_trip_conforms_to_contract(conn) -> None:
    claim_id = _cid()
    stored = agency_claims.record_claim(
        conn,
        claim_id=claim_id,
        project_id="project-fictional-01",
        claim_type="zone_plu",
        value="UB",
        backing_card_ref={"card_family": "knowledge", "card_id": "knowledge.plu.ub"},
        provenance={"source_kind": "document", "source_ref": "document.plu.2024"},
        status="source_backed",
        observed_at="2026-07-25T14:30:00Z",
        revision=1,
        note="zone displayed is not a regulatory conclusion",
    )
    assert stored["claim_id"] == claim_id
    assert stored["backing_card_ref"]["card_family"] == "knowledge"
    assert stored["provenance"]["source_kind"] == "document"
    # get_claim and list both re-validate; a round-trip that returns is proof.
    assert agency_claims.get_claim(conn, claim_id)["value"] == "UB"


def test_value_scalar_types_survive_the_round_trip(conn) -> None:
    cases = {
        "surface": 128.5,
        "erp_flag": True,
        "permit_status": "granted",
        "missing_zone": None,
    }
    project = "project-fictional-types"
    for claim_type, value in cases.items():
        agency_claims.record_claim(
            conn,
            claim_id=_cid(claim_type),
            project_id=project,
            claim_type=claim_type,
            value=value,
            backing_card_ref={"card_family": "surface_fact", "card_id": f"card.{claim_type}"},
            provenance={"source_kind": "derived"},
            status="asserted",
            observed_at="2026-07-25T10:00:00Z",
        )
    by_type = {c["claim_type"]: c["value"] for c in agency_claims.list_project_claims(conn, project)}
    assert by_type == cases


def test_list_is_scoped_and_can_exclude_retired(conn) -> None:
    project = "project-fictional-scope"
    other = "project-fictional-other"
    agency_claims.record_claim(
        conn, claim_id=_cid(), project_id=project, claim_type="risk", value="moyen",
        backing_card_ref={"card_family": "evidence", "card_id": "e.georisque"},
        provenance={"source_kind": "document"}, status="source_backed",
        observed_at="2026-07-25T09:00:00Z",
    )
    agency_claims.record_claim(
        conn, claim_id=_cid(), project_id=project, claim_type="risk", value="faible",
        backing_card_ref={"card_family": "evidence", "card_id": "e.georisque.old"},
        provenance={"source_kind": "document"}, status="retired",
        observed_at="2026-07-24T09:00:00Z",
    )
    agency_claims.record_claim(
        conn, claim_id=_cid(), project_id=other, claim_type="risk", value="fort",
        backing_card_ref={"card_family": "evidence", "card_id": "e.other"},
        provenance={"source_kind": "document"}, status="source_backed",
        observed_at="2026-07-25T09:00:00Z",
    )
    assert len(agency_claims.list_project_claims(conn, project)) == 2
    active = agency_claims.list_project_claims(conn, project, include_retired=False)
    assert len(active) == 1
    assert active[0]["status"] == "source_backed"


def test_bad_claim_is_refused_before_touching_the_database(conn) -> None:
    with pytest.raises(agency_claims.ClaimContractViolation):
        agency_claims.record_claim(
            conn,
            claim_id="Bad Id",
            project_id="project-fictional-01",
            claim_type="zone_plu",
            value="UB",
            backing_card_ref={"card_family": "knowledge", "card_id": "k.x"},
            provenance={"source_kind": "document"},
            status="source_backed",
            observed_at="2026-07-25T14:30:00Z",
        )
    # Nothing was written.
    assert agency_claims.list_project_claims(conn, "project-fictional-01") == []
