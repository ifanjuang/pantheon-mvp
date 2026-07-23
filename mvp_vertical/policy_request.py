"""Build the exact Pantheon HTTP preflight body expected by the PDP.

Runtime adapters often know an effect in their own vocabulary (Paperless
metadata update, capability install, project-document intake). The Pantheon
policy HTTP contract is deliberately generic and expects only ``request`` plus
``gate_signals``. This module performs that adapter translation without adding
policy or authority.
"""

from __future__ import annotations

from typing import Any


_REQUEST_FIELDS = frozenset(
    {
        "intent",
        "external_effect",
        "writes_state",
        "transmission_requested",
        "memory_promotion_requested",
        "professional_position",
        "financial_or_contractual_effect",
        "scope",
    }
)

_GATE_FIELDS = frozenset(
    {
        "task_contract_ref",
        "evidence_pack_candidate_ref",
        "human_decision_ref",
        "human_decision_level",
    }
)


def _scope_from_decision(decision_payload: dict[str, Any]) -> dict[str, Any] | None:
    expectation = decision_payload.get("expectation") or {}
    decision = decision_payload.get("decision") or {}
    scope = expectation.get("required_scope") or decision.get("scope")
    return dict(scope) if isinstance(scope, dict) else None


def build_preflight_payload(
    candidate: dict[str, Any],
    decision_payload: dict[str, Any],
) -> dict[str, Any]:
    """Translate one runtime candidate to ``pantheon.policy.v1`` preflight input.

    The returned mapping intentionally contains only the two top-level fields
    defined by ``mcp-server/docs/HTTP_API_CONTRACT.md``. Runtime-specific keys
    such as ``effect_kind`` and ``document_id`` remain local trace data and are
    not leaked into the policy transport schema.

    Callers may provide an explicit ``request`` / ``gate_signals`` mapping. When
    they provide only runtime-specific fields, conservative defaults are used:
    a consequential effect is assumed to write state and affect an external
    runtime unless the caller explicitly says otherwise. Missing scope is left
    missing so the PDP can fail closed with ``blocked_pending_scope``.
    """

    explicit_request = candidate.get("request")
    if explicit_request is not None and not isinstance(explicit_request, dict):
        raise ValueError("candidate.request must be a mapping")

    source_request = explicit_request or {}
    request: dict[str, Any] = {
        key: source_request[key]
        for key in _REQUEST_FIELDS
        if key in source_request
    }

    request.setdefault(
        "intent",
        str(
            candidate.get("intent")
            or candidate.get("effect_kind")
            or candidate.get("action")
            or "consequential_effect"
        ),
    )
    request.setdefault("external_effect", bool(candidate.get("external_effect", True)))
    request.setdefault("writes_state", bool(candidate.get("writes_state", True)))
    request.setdefault(
        "transmission_requested", bool(candidate.get("transmission_requested", False))
    )
    request.setdefault(
        "memory_promotion_requested", bool(candidate.get("memory_promotion_requested", False))
    )
    request.setdefault(
        "professional_position", bool(candidate.get("professional_position", False))
    )
    request.setdefault(
        "financial_or_contractual_effect",
        bool(candidate.get("financial_or_contractual_effect", False)),
    )

    if "scope" not in request:
        scope = candidate.get("scope")
        if isinstance(scope, dict):
            request["scope"] = dict(scope)
        else:
            inferred_scope = _scope_from_decision(decision_payload)
            if inferred_scope is not None:
                request["scope"] = inferred_scope

    explicit_signals = candidate.get("gate_signals")
    if explicit_signals is not None and not isinstance(explicit_signals, dict):
        raise ValueError("candidate.gate_signals must be a mapping")

    source_signals = explicit_signals or {}
    gate_signals: dict[str, Any] = {
        key: source_signals[key]
        for key in _GATE_FIELDS
        if source_signals.get(key) not in (None, "")
    }

    for key in ("task_contract_ref", "evidence_pack_candidate_ref"):
        if key not in gate_signals and candidate.get(key) not in (None, ""):
            gate_signals[key] = candidate[key]

    decision = decision_payload.get("decision") or {}
    if gate_signals.get("human_decision_ref") in (None, "") and decision.get("decision_id"):
        gate_signals["human_decision_ref"] = decision["decision_id"]
    if gate_signals.get("human_decision_level") in (None, "") and decision.get("approval_level"):
        gate_signals["human_decision_level"] = decision["approval_level"]

    return {
        "request": request,
        "gate_signals": gate_signals,
    }
