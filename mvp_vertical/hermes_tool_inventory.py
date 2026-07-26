"""Read-only Hermes inventory adapter for Tool Card projections.

The adapter knows only verified Hermes HTTP discovery surfaces. It does not read
arbitrary Hermes files, install/enable skills, execute tools, approve capabilities
or infer Pantheon activation from native runtime state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable
from urllib.request import urlopen

from .document_runtime_network_observer import _bounded_json_value, _safe_base_url


def _observed_at() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _items(payload: Any, key: str) -> list[dict[str, Any]]:
    raw = payload if isinstance(payload, list) else payload.get(key, []) if isinstance(payload, dict) else []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _stable_id(prefix: str, value: str) -> str:
    normalized = "-".join(value.strip().lower().replace("_", "-").split())
    return f"hermes-{prefix}-{normalized}"


def normalize_hermes_inventory(
    *,
    skills_payload: Any,
    toolsets_payload: Any,
    capabilities_payload: Any,
    observed_at: str | None = None,
) -> list[dict[str, Any]]:
    """Normalize verified Hermes discovery payloads into Tool Card observations."""
    stamp = observed_at or _observed_at()
    observations: list[dict[str, Any]] = []

    for skill in _items(skills_payload, "skills"):
        name = str(skill.get("name") or skill.get("id") or "").strip()
        if not name:
            continue
        enabled = skill.get("enabled")
        observations.append({
            "tool_id": _stable_id("skill", name),
            "name": name,
            "provenance_mode": "hermes_dynamic_skill",
            "native_identifier": name,
            "source_repository": skill.get("source_repository") or skill.get("repository"),
            "version": skill.get("version"),
            "installation_state": "installed",
            "native_state": "enabled" if enabled is True else "disabled" if enabled is False else "unknown",
            "health_state": "unknown",
            "governance_state": "unreviewed",
            "update_state": "update_unknown",
            "activation_state": "not_activated",
            "observed_at": stamp,
            "capabilities": [],
            "permissions": [],
        })

    for toolset in _items(toolsets_payload, "toolsets"):
        name = str(toolset.get("name") or "").strip()
        if not name:
            continue
        tools = [str(tool) for tool in (toolset.get("tools") or []) if str(tool).strip()]
        configured = toolset.get("configured")
        enabled = toolset.get("enabled")
        native_state = "enabled" if configured is True and enabled is True else "disabled" if enabled is False else "configured" if configured is True else "unknown"
        observations.append({
            "tool_id": _stable_id("toolset", name),
            "name": name,
            "provenance_mode": "hermes_native_inventory",
            "native_identifier": name,
            "source_repository": None,
            "version": None,
            "installation_state": "installed",
            "native_state": native_state,
            "health_state": "unknown",
            "governance_state": "unreviewed",
            "update_state": "update_unknown",
            "activation_state": "not_activated",
            "observed_at": stamp,
            "capabilities": tools,
            "permissions": [],
        })

    if isinstance(capabilities_payload, dict):
        features = capabilities_payload.get("features") or {}
        if isinstance(features, dict):
            active = sorted(str(key) for key, value in features.items() if value is True)
            observations.append({
                "tool_id": "hermes-api-server",
                "name": "Hermes API Server",
                "provenance_mode": "hermes_native_inventory",
                "native_identifier": "hermes.api_server.capabilities",
                "source_repository": None,
                "version": capabilities_payload.get("version"),
                "installation_state": "installed",
                "native_state": "enabled",
                "health_state": "observed_ready",
                "governance_state": "unreviewed",
                "update_state": "update_unknown",
                "activation_state": "not_activated",
                "observed_at": stamp,
                "capabilities": active,
                "permissions": [],
            })

    return observations


def observe_hermes_tool_inventory(
    base_url: str,
    api_key: str,
    *,
    timeout: float = 8.0,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    """Read verified Hermes inventory endpoints and return normalized observations."""
    stamp = _observed_at()
    if not api_key:
        return {"status": "not_configured", "observed_at": stamp, "capabilities": []}
    try:
        base = _safe_base_url(base_url, "Hermes API URL")
    except ValueError as exc:
        return {"status": "configuration_error", "observed_at": stamp, "capabilities": [], "detail": str(exc)}

    headers = {"Authorization": f"Bearer {api_key}"}
    payloads: dict[str, Any] = {}
    statuses: dict[str, int] = {}
    for key, path in (("skills", "/v1/skills"), ("toolsets", "/v1/toolsets"), ("capabilities", "/v1/capabilities")):
        status, payload = _bounded_json_value(base + path, headers=headers, timeout=timeout, opener=opener)
        statuses[key] = status
        if not 200 <= status < 300:
            return {
                "status": "unavailable",
                "observed_at": stamp,
                "capabilities": [],
                "surface_status": statuses,
                "failed_surface": path,
                "authority_effect": "none",
            }
        payloads[key] = payload

    normalized = normalize_hermes_inventory(
        skills_payload=payloads["skills"],
        toolsets_payload=payloads["toolsets"],
        capabilities_payload=payloads["capabilities"],
        observed_at=stamp,
    )
    return {
        "status": "observed",
        "observation_source": "hermes_verified_discovery_api",
        "observed_at": stamp,
        "capabilities": normalized,
        "surface_status": statuses,
        "authority_effect": "none",
        "write_effect": False,
        "activation_changed": False,
        "non_equivalences": [
            "listed != approved",
            "installed != approved",
            "enabled != Pantheon activated",
            "healthy != safe",
            "runtime observation != Evidence",
        ],
    }
