"""Server-calculated read-only Project Anatomy projection.

The executable APU owner remains authoritative. This module only calculates a
Cockpit read model; it persists nothing, authorizes nothing and admits no Evidence.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from psycopg.rows import dict_row

from . import apu_owner

ATTENTION_PROOF_STATUSES = {
    "source_missing",
    "source_incomplete",
    "contradictory_evidence",
    "authority_too_low",
    "requires_more_evidence",
}
INACTIVE_IDENTITY_STATUSES = {"rejected", "obsolete", "superseded", "source_superseded"}


def _entity_id(ref: Any, entity_type: str) -> str | None:
    if not isinstance(ref, dict) or ref.get("entity_type") != entity_type:
        return None
    value = str(ref.get("entity_id") or "").strip()
    return value or None


def _phase_refs(claim: dict[str, Any]) -> list[str]:
    validity = claim.get("validity") if isinstance(claim.get("validity"), dict) else {}
    value = str(validity.get("established_at_phase") or "").strip()
    return [value] if value else []


def _claim_summary(claim: dict[str, Any], claim_type: str) -> dict[str, Any]:
    result = {
        "claim_type": claim_type,
        "claim_id": claim.get("attribute_claim_id" if claim_type == "attribute_claim" else "relation_claim_id"),
        "proof_status": claim.get("proof_status"),
        "certainty": claim.get("certainty"),
        "assertion_mode": claim.get("assertion_mode"),
        "source_authority": claim.get("source_authority"),
        "source_representation_refs": list(claim.get("source_representation_refs") or []),
        "phase_refs": _phase_refs(claim),
    }
    if claim_type == "attribute_claim":
        result.update(attribute_key=claim.get("attribute_key"), value=claim.get("value"))
    else:
        result.update(
            relation_type=claim.get("relation_type"),
            subject_ref=claim.get("subject_ref"),
            object_ref=claim.get("object_ref"),
        )
    return result


def build_project_anatomy_projection(anatomy: dict[str, Any], *, model_doctrine_ref: str | None) -> dict[str, Any]:
    stable_entries = list(anatomy.get("stable_objects") or [])
    representations = list(anatomy.get("source_representations") or [])
    attribute_claims = list(anatomy.get("attribute_claims") or [])
    relation_claims = list(anatomy.get("relation_claims") or [])

    representation_ids = {
        str(item.get("representation_id"))
        for item in representations
        if str(item.get("representation_id") or "").strip()
    }
    mapped_by_representation: dict[str, set[str]] = defaultdict(set)
    mapped_by_object: dict[str, set[str]] = defaultdict(set)
    for claim in relation_claims:
        if claim.get("relation_type") != "identity.represents" or claim.get("proof_status") in INACTIVE_IDENTITY_STATUSES:
            continue
        representation_id = _entity_id(claim.get("subject_ref"), "source_representation")
        object_id = _entity_id(claim.get("object_ref"), "stable_object")
        if representation_id and object_id:
            mapped_by_representation[representation_id].add(object_id)
            mapped_by_object[object_id].add(representation_id)

    attributes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    relations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    phases: dict[str, set[str]] = defaultdict(set)
    sources: dict[str, set[str]] = defaultdict(set)
    attention: dict[str, set[str]] = defaultdict(set)

    for claim in attribute_claims:
        object_id = _entity_id(claim.get("subject_ref"), "stable_object")
        if not object_id:
            continue
        attributes[object_id].append(_claim_summary(claim, "attribute_claim"))
        phases[object_id].update(_phase_refs(claim))
        sources[object_id].update(claim.get("source_representation_refs") or [])
        if claim.get("proof_status") in ATTENTION_PROOF_STATUSES:
            attention[object_id].add(str(claim.get("attribute_claim_id")))

    relation_edges = []
    for claim in relation_claims:
        subject_id = _entity_id(claim.get("subject_ref"), "stable_object")
        object_id = _entity_id(claim.get("object_ref"), "stable_object")
        if not subject_id or not object_id:
            continue
        summary = _claim_summary(claim, "relation_claim")
        relation_edges.append(summary)
        for stable_id in {subject_id, object_id}:
            relations[stable_id].append(summary)
            phases[stable_id].update(_phase_refs(claim))
            sources[stable_id].update(claim.get("source_representation_refs") or [])
            if claim.get("proof_status") in ATTENTION_PROOF_STATUSES:
                attention[stable_id].add(str(claim.get("relation_claim_id")))

    objects = []
    for entry in stable_entries:
        stable = dict(entry.get("stable_object") or {})
        object_id = str(stable.get("stable_object_id") or entry.get("object_id") or "").strip()
        nomenclature = stable.get("nomenclature") if isinstance(stable.get("nomenclature"), dict) else {}
        object_sources = set(sources[object_id]) | mapped_by_object[object_id]
        objects.append({
            "object_id": object_id,
            "object_family": stable.get("object_family"),
            "display_name": nomenclature.get("display_name") or nomenclature.get("internal_code") or object_id,
            "internal_code": nomenclature.get("internal_code"),
            "aliases": list(nomenclature.get("aliases") or []),
            "revision": entry.get("revision"),
            "attribute_claims": attributes[object_id],
            "relations": relations[object_id],
            "source_representation_refs": sorted(ref for ref in object_sources if ref in representation_ids),
            "phase_refs": sorted(phases[object_id]),
            "attention_claim_refs": sorted(attention[object_id]),
        })

    source_lens = []
    for item in representations:
        representation_id = str(item.get("representation_id") or "").strip()
        source_lens.append({
            "representation_id": representation_id,
            "source_artifact_ref": item.get("source_artifact_ref"),
            "source_version_ref": item.get("source_version_ref"),
            "source_kind": item.get("source_kind"),
            "observed_at": item.get("observed_at"),
            "proof_status": item.get("proof_status"),
            "binding_ref": item.get("binding_ref"),
            "adapter_version": item.get("adapter_version"),
            "locators": list(item.get("locators") or []),
            "limitations": list(item.get("limitations") or []),
            "context": item.get("context") or {},
            "mapped_object_refs": sorted(mapped_by_representation[representation_id]),
        })
    unmapped = [item for item in source_lens if not item["mapped_object_refs"]]
    attention_claims = [
        _claim_summary(claim, "attribute_claim") for claim in attribute_claims
        if claim.get("proof_status") in ATTENTION_PROOF_STATUSES
    ] + [
        _claim_summary(claim, "relation_claim") for claim in relation_claims
        if claim.get("proof_status") in ATTENTION_PROOF_STATUSES
    ]

    authority = dict(anatomy.get("authority") or {})
    authority.update({
        "cockpit_projection_only": True,
        "authorization_inferred": False,
        "absence_inferred": False,
        "hierarchy_inferred_without_registered_semantics": False,
    })
    return {
        "project_ref": anatomy.get("project_ref"),
        "model_version": anatomy.get("model_version"),
        "model_authority_ref": anatomy.get("model_authority_ref"),
        "model_doctrine_ref": model_doctrine_ref,
        "owner_revision": anatomy.get("owner_revision"),
        "summary": {
            "stable_object_count": len(objects),
            "source_representation_count": len(source_lens),
            "attribute_claim_count": len(attribute_claims),
            "relation_claim_count": len(relation_claims),
            "unmapped_source_representation_count": len(unmapped),
            "attention_claim_count": len(attention_claims),
            "limited_source_count": sum(bool(item["limitations"]) for item in source_lens),
        },
        "structure": {
            "objects": objects,
            "object_family_counts": {
                family: sum(item.get("object_family") == family for item in objects)
                for family in sorted({item.get("object_family") for item in objects if item.get("object_family")})
            },
            "hierarchy": {
                "status": "not_derived",
                "reason": "No admitted hierarchy-relation registry exists; relation claims are not reinterpreted as parentage.",
            },
        },
        "relations": relation_edges,
        "sources": source_lens,
        "uncertainty": {
            "attention_proof_statuses": sorted(ATTENTION_PROOF_STATUSES),
            "claims_requiring_attention": attention_claims,
            "certainty_is_reported_not_approved": True,
        },
        "unmapped_material": unmapped,
        "coverage": {
            "status": "not_persisted",
            "reason": "Observation Bundle coverage is not persisted by the current executable APU owner.",
            "absence_inference_allowed": False,
        },
        "compatibility": dict(anatomy.get("compatibility") or {}),
        "authority": authority,
    }


def get_project_anatomy_projection(conn, *, project_id: str) -> dict[str, Any]:
    anatomy = apu_owner.get_project_anatomy_v02(conn, project_id=project_id)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT model_doctrine_ref FROM agency_apu_project_state WHERE project_id = %s", (project_id,))
        row = cur.fetchone()
    return build_project_anatomy_projection(
        anatomy,
        model_doctrine_ref=row.get("model_doctrine_ref") if row else None,
    )
