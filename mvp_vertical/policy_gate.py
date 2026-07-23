"""Policy chokepoint seam (Phase C): a consequential effect routes through the
Pantheon policy check before it happens.

This repository does not embed the Pantheon policy service. It defines the seam
the runtime uses to consult a Policy Decision Point (Pantheon `mcp-server`) and
to enforce the verdict — the Policy Enforcement Point role. A real deployment
injects an HTTP client to that PDP; tests inject the deterministic stand-in
below.

Two rules make this a real chokepoint, not advice:

- **Fail closed.** If the policy client is unavailable, the adapter payload is
  malformed, or the verdict is not a clear eligible result, the consequential
  effect is blocked and never runs.
- **Smart-approvals neutralized.** The seam never auto-approves. Only an eligible
  preflight *and* a valid human decision reference permit the effect; an
  in-runtime "smart approval" cannot substitute for that decision.

New bindings must also bind the decision expectation to effect facts observed by
the PEP (scope, object identity, digest and required ceiling). The caller cannot
weaken those facts by sending a matching but false expectation.

`STAND-IN`: `StandInPolicyClient` occupies the PDP seat for offline tests. It is
not the Pantheon policy service:

    stand_in_policy_client != Pantheon PDP
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .policy_request import bind_decision_payload, build_preflight_payload

_ELIGIBLE_DISPOSITIONS = frozenset(
    {"eligible_for_candidate_work", "eligible_with_gate_signals_unverified"}
)


class PolicyClient(Protocol):
    """The bounded surface the PEP consults. It never executes the effect."""

    def preflight(self, candidate: dict[str, Any]) -> dict[str, Any]:
        ...

    def validate_decision(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class GateVerdict:
    allowed: bool
    disposition: str
    reasons: list[str] = field(default_factory=list)


def enforce_consequential(
    client: PolicyClient,
    *,
    candidate: dict[str, Any],
    decision_payload: dict[str, Any],
) -> GateVerdict:
    """Consult the PDP and return whether the consequential effect may proceed.

    Runtime-specific candidates are first normalized to the generic Pantheon
    preflight body. When the adapter supplies ``decision_expectation``, the human
    decision is validated against those PEP-owned effect facts rather than a
    caller-authored expectation.
    """

    try:
        bound_decision = bind_decision_payload(candidate, decision_payload)
        preflight_payload = build_preflight_payload(candidate, bound_decision)
        preflight = client.preflight(preflight_payload)
    except Exception as exc:  # unavailable / malformed adapter payload -> fail closed
        return GateVerdict(False, "policy_unavailable", [f"preflight call failed: {exc}"])

    disposition = str(preflight.get("policy_disposition", "unknown"))
    if disposition not in _ELIGIBLE_DISPOSITIONS:
        reasons = [f"preflight disposition: {disposition}"]
        reasons += list(preflight.get("missing_requirements", []))
        return GateVerdict(False, disposition, reasons)

    try:
        validation = client.validate_decision(bound_decision)
    except Exception as exc:
        return GateVerdict(False, "policy_unavailable", [f"decision validation failed: {exc}"])

    if validation.get("verdict") != "valid":
        reasons = [f"decision verdict: {validation.get('verdict', 'unknown')}"]
        reasons += list(validation.get("findings", []))
        return GateVerdict(False, disposition, reasons)

    return GateVerdict(True, disposition, [])


def governed_effect(
    client: PolicyClient,
    *,
    candidate: dict[str, Any],
    decision_payload: dict[str, Any],
    effect: Callable[[], Any],
) -> dict[str, Any]:
    """Run a consequential ``effect`` only behind the bounded chokepoint."""

    verdict = enforce_consequential(
        client, candidate=candidate, decision_payload=decision_payload
    )
    if not verdict.allowed:
        return {
            "status": "blocked",
            "disposition": verdict.disposition,
            "reasons": verdict.reasons,
            "effect_ran": False,
        }
    return {
        "status": "applied",
        "disposition": verdict.disposition,
        "effect_ran": True,
        "result": effect(),
    }


class StandInPolicyClient:
    """Deterministic offline PDP stand-in for tests; not Pantheon authority."""

    _SYSTEM_PREFIXES = ("system", "service", "runtime", "hermes", "bot", "agent")

    def __init__(self, *, disposition: str = "eligible_for_candidate_work"):
        self._disposition = disposition
        self.last_preflight: dict[str, Any] | None = None
        self.last_decision: dict[str, Any] | None = None

    def preflight(self, candidate: dict[str, Any]) -> dict[str, Any]:
        self.last_preflight = candidate
        return {"policy_disposition": self._disposition, "missing_requirements": []}

    def validate_decision(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.last_decision = payload
        decision = payload.get("decision") or {}
        expectation = payload.get("expectation") or {}
        findings: list[str] = []
        signer = str(decision.get("decided_by", "")).strip().lower()
        if not signer or signer.split(":", 1)[0].split("-", 1)[0] in self._SYSTEM_PREFIXES:
            findings.append("decided_by is empty or a non-human identity")
        req_scope = expectation.get("required_scope")
        if req_scope is not None and decision.get("scope") != req_scope:
            findings.append("decision scope does not match required scope")
        required_ceiling = expectation.get("required_ceiling")
        if required_ceiling is not None and decision.get("approval_level") != required_ceiling:
            findings.append("decision approval_level does not match required ceiling")
        object_identity = expectation.get("object_identity")
        if object_identity is not None and decision.get("object_identity") != object_identity:
            findings.append("decision object_identity does not match effect object")
        expected_digest = expectation.get("expected_digest")
        if expected_digest is not None and decision.get("content_digest") != expected_digest:
            findings.append("decision content_digest does not match effect digest")
        verdict = "valid" if not findings else "invalid"
        return {"verdict": verdict, "findings": findings}


class HttpPolicyClient:
    """Real ``PolicyClient`` for the Pantheon internal HTTP PDP.

    `enforce_consequential` normalizes the preflight and binds the decision
    expectation before either request reaches this transport client. Transport
    errors remain fail-closed at the PEP seam.
    """

    _PREFLIGHT = "/v1/policy/preflights:evaluate"
    _VALIDATE = "/v1/policy/decisions:validate"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 5.0,
        client: Any | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client = client

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        client = self._client
        owns = client is None
        if owns:
            import httpx

            client = httpx.Client(timeout=self._timeout)
        try:
            response = client.post(
                self._base_url + path,
                json=body,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.json()
        finally:
            if owns:
                client.close()

    def preflight(self, candidate: dict[str, Any]) -> dict[str, Any]:
        return self._post(self._PREFLIGHT, candidate)

    def validate_decision(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post(self._VALIDATE, payload)
