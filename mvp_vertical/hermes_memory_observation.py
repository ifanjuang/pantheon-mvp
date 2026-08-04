"""Read-only capture and qualification of one Hermes profile memory posture.

The capture invokes only the official ``hermes -p <profile> memory status``
command without a shell. It does not mutate configuration, read arbitrary
profile files, enable or disable tools, or retain the command's raw output.

The resulting receipt is a technical observation, not Evidence, approval,
activation or task authorization.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import datetime, timezone
from typing import Any, Callable


MAX_MEMORY_STATUS_CHARS = 64_000
_PROFILE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_ANSI_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


class HermesMemoryObservationError(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_profile_name(value: str) -> str:
    profile = str(value or "").strip()
    if not profile or not _PROFILE_PATTERN.fullmatch(profile):
        raise HermesMemoryObservationError(
            "Hermes profile must contain only letters, numbers, hyphens or underscores"
        )
    return profile


def _toggle(text: str, label: str) -> str:
    match = re.search(
        rf"^\s*{re.escape(label)}\s*:\s*(enabled|disabled)\b",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        return "unknown"
    return "on" if match.group(1).lower() == "enabled" else "off"


def _provider(text: str) -> str:
    match = re.search(r"^\s*Provider\s*:\s*(.*?)\s*$", text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return "unknown"
    value = match.group(1).strip().lower()
    if not value:
        return "unknown"
    if value.startswith("(none") or "built-in only" in value or "builtin only" in value:
        return "off"
    return "selected"


def parse_memory_status(
    output: str,
    *,
    profile: str,
    command: list[str] | None = None,
    exit_code: int = 0,
    captured_at: str | None = None,
) -> dict[str, Any]:
    """Parse official human-readable memory status into a bounded receipt."""

    profile = normalize_profile_name(profile)
    if not isinstance(output, str):
        raise HermesMemoryObservationError("Hermes memory status output must be text")
    if len(output) > MAX_MEMORY_STATUS_CHARS:
        raise HermesMemoryObservationError(
            f"Hermes memory status output exceeds {MAX_MEMORY_STATUS_CHARS} characters"
        )

    normalized = _ANSI_PATTERN.sub("", output).replace("\r\n", "\n").replace("\r", "\n")
    axes = {
        "external_provider": _provider(normalized),
        "built_in_memory_injection": _toggle(normalized, "Memory injection"),
        "built_in_user_profile_injection": _toggle(normalized, "User profile"),
        "memory_tool": _toggle(normalized, "Memory tool"),
    }
    missing = sorted(name for name, value in axes.items() if value == "unknown")
    active = sorted(name for name, value in axes.items() if value in {"on", "selected"})

    if exit_code != 0:
        status = "not_qualified"
        reason = "Hermes memory status command did not exit successfully"
    elif missing:
        status = "not_qualified"
        reason = "Hermes memory status output is incomplete"
    elif active:
        status = "not_qualified"
        reason = "Hermes governed memory posture contains active memory inputs"
    else:
        status = "qualified"
        reason = None

    return {
        "kind": "hermes_profile_memory_observation",
        "observation_source": "hermes_memory_status_cli",
        "profile": profile,
        "captured_at": captured_at or _now(),
        "command": list(command or ["hermes", "-p", profile, "memory", "status"]),
        "exit_code": int(exit_code),
        "stdout_digest": "sha256:" + hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "raw_output_retained": False,
        **axes,
        "missing_axes": missing,
        "active_axes": active,
        "status": status,
        "reason": reason,
        "write_effect": False,
        "activation_changed": False,
        "authority_effect": "none",
        "technical_receipt_is_evidence": False,
        "non_equivalences": [
            "hermes memory off != built-in memory injection off",
            "memory tool absent != memory injection disabled",
            "stored memory != admitted memory",
            "memory observation != Evidence",
        ],
    }


def capture_memory_status(
    *,
    profile: str,
    hermes_command: str = "hermes",
    timeout: float = 10.0,
    runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Capture one profile-local status command without a shell or mutation."""

    profile = normalize_profile_name(profile)
    command_name = str(hermes_command or "").strip()
    if not command_name:
        raise HermesMemoryObservationError("Hermes command is required")
    if timeout <= 0:
        raise HermesMemoryObservationError("Hermes memory status timeout must be positive")

    command = [command_name, "-p", profile, "memory", "status"]
    run = runner or subprocess.run
    try:
        completed = run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise HermesMemoryObservationError("Hermes memory status capture failed") from exc

    stdout = completed.stdout if isinstance(completed.stdout, str) else ""
    return parse_memory_status(
        stdout,
        profile=profile,
        command=command,
        exit_code=int(completed.returncode),
    )


def qualify_memory_observation(
    receipt: dict[str, Any] | None,
    *,
    expected_profile: str | None,
) -> dict[str, Any]:
    """Fail closed when a supplied receipt is incomplete, mismatched or active."""

    if receipt is None:
        return {
            "status": "not_evaluated",
            "expected_profile": expected_profile,
            "observed_profile": None,
            "external_provider": "unknown",
            "built_in_memory_injection": "unknown",
            "built_in_user_profile_injection": "unknown",
            "memory_tool": "unknown",
            "session_memory_key": "absent",
            "reason": "no profile memory observation was supplied",
            "missing_axes": [
                "external_provider",
                "built_in_memory_injection",
                "built_in_user_profile_injection",
                "memory_tool",
            ],
            "active_axes": [],
            "observation_source": None,
            "stdout_digest": None,
        }
    if not isinstance(receipt, dict):
        raise HermesMemoryObservationError("Hermes memory observation must be an object")
    if receipt.get("kind") != "hermes_profile_memory_observation":
        raise HermesMemoryObservationError("Hermes memory observation has an unexpected kind")

    observed_profile = normalize_profile_name(str(receipt.get("profile") or ""))
    expected = normalize_profile_name(expected_profile) if expected_profile else None
    valid_values = {
        "external_provider": {"off", "selected", "unknown"},
        "built_in_memory_injection": {"off", "on", "unknown"},
        "built_in_user_profile_injection": {"off", "on", "unknown"},
        "memory_tool": {"off", "on", "unknown"},
    }
    axes: dict[str, str] = {}
    for name, allowed in valid_values.items():
        value = str(receipt.get(name) or "unknown")
        if value not in allowed:
            raise HermesMemoryObservationError(f"Hermes memory observation has invalid {name}")
        axes[name] = value

    missing = sorted(name for name, value in axes.items() if value == "unknown")
    active = sorted(name for name, value in axes.items() if value in {"on", "selected"})
    reasons: list[str] = []
    if expected is None:
        reasons.append("no expected profile was supplied")
    elif observed_profile != expected:
        reasons.append("memory observation profile differs from expected profile")
    if receipt.get("exit_code") != 0:
        reasons.append("memory status command did not exit successfully")
    if receipt.get("status") != "qualified":
        reasons.append("memory observation is not qualified")
    if missing:
        reasons.append("memory observation has missing axes")
    if active:
        reasons.append("memory observation has active axes")

    status = "qualified" if not reasons else "not_qualified"
    return {
        "status": status,
        "expected_profile": expected,
        "observed_profile": observed_profile,
        **axes,
        "session_memory_key": "absent",
        "reason": None if status == "qualified" else "; ".join(reasons),
        "missing_axes": missing,
        "active_axes": active,
        "observation_source": receipt.get("observation_source"),
        "stdout_digest": receipt.get("stdout_digest"),
        "raw_output_retained": receipt.get("raw_output_retained") is True,
    }
