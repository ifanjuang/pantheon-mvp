"""Runtime profile and observation normalization at the adapter boundary.

This module records what an external runtime reports or what an adapter observes.
It does not install, activate, authorize, schedule, dispatch, or promote Evidence.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Mapping


SUPPORT_STATES = {"unknown", "reported", "observed", "unavailable"}
COMPATIBILITY_STATES = {"unknown", "compatible", "degraded", "incompatible", "stale"}
OBSERVATION_KINDS = {
    "started",
    "progress",
    "completed",
    "failed",
    "capability_gap",
    "risk_escalation",
}


class RuntimeProfileValidationError(ValueError):
    """Raised when runtime adapter data is incomplete or invalid."""


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeProfileValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _timestamp(value: Any, field: str) -> str:
    raw = _required_string(value, field)
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeProfileValidationError(f"{field} must be an ISO-8601 timestamp") from exc
    return raw


def _string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise RuntimeProfileValidationError(f"{field} must be a list of non-empty strings")
    return list(value)


def normalize_runtime_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one observed external runtime profile.

    Capability names remain adapter data. Only their support state is governed here,
    which prevents release-specific capability names from becoming backend identity.
    """

    if not isinstance(profile, Mapping):
        raise RuntimeProfileValidationError("runtime profile must be an object")

    compatibility = profile.get("compatibility_status", "unknown")
    if compatibility not in COMPATIBILITY_STATES:
        raise RuntimeProfileValidationError("unsupported compatibility_status")

    capabilities = profile.get("capabilities", {})
    if not isinstance(capabilities, Mapping):
        raise RuntimeProfileValidationError("capabilities must be an object")

    normalized_capabilities: dict[str, dict[str, Any]] = {}
    for capability_name, capability_value in capabilities.items():
        name = _required_string(capability_name, "capability name")
        if not isinstance(capability_value, Mapping):
            raise RuntimeProfileValidationError(f"capabilities.{name} must be an object")
        support = capability_value.get("support", "unknown")
        if support not in SUPPORT_STATES:
            raise RuntimeProfileValidationError(f"unsupported support state for capabilities.{name}")
        normalized_capabilities[name] = deepcopy(dict(capability_value))
        normalized_capabilities[name]["support"] = support

    return {
        "runtime_id": _required_string(profile.get("runtime_id"), "runtime_id"),
        "binding_id": _required_string(profile.get("binding_id"), "binding_id"),
        "runtime_version": _required_string(profile.get("runtime_version"), "runtime_version"),
        "api_version": _required_string(profile.get("api_version", "unknown"), "api_version"),
        "observed_at": _timestamp(profile.get("observed_at"), "observed_at"),
        "observed_by": _required_string(profile.get("observed_by"), "observed_by"),
        "compatibility_status": compatibility,
        "capabilities": normalized_capabilities,
        "source_refs": _string_list(profile.get("source_refs"), "source_refs"),
        "trace_refs": _string_list(profile.get("trace_refs"), "trace_refs"),
        "risk_notes": _string_list(profile.get("risk_notes"), "risk_notes"),
    }


def normalize_runtime_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one runtime observation without interpreting it as Evidence."""

    if not isinstance(observation, Mapping):
        raise RuntimeProfileValidationError("runtime observation must be an object")

    kind = observation.get("kind")
    if kind not in OBSERVATION_KINDS:
        raise RuntimeProfileValidationError("unsupported runtime observation kind")

    payload = observation.get("payload", {})
    if not isinstance(payload, Mapping):
        raise RuntimeProfileValidationError("payload must be an object")

    return {
        "observation_id": _required_string(observation.get("observation_id"), "observation_id"),
        "runtime_id": _required_string(observation.get("runtime_id"), "runtime_id"),
        "runtime_version": _required_string(observation.get("runtime_version"), "runtime_version"),
        "run_id": _required_string(observation.get("run_id"), "run_id"),
        "kind": kind,
        "observed_at": _timestamp(observation.get("observed_at"), "observed_at"),
        "payload": deepcopy(dict(payload)),
        "trace_refs": _string_list(observation.get("trace_refs"), "trace_refs"),
    }
