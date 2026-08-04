#!/usr/bin/env python3
"""Operator-facing harness for an ephemeral Hermes Agent 0.20.0 lab acceptance.

The harness configures only an isolated HERMES_HOME supplied by the caller,
waits for bounded local HTTP surfaces, and validates the technical receipts
created by the real Hermes and Pantheon bridge CLIs. It does not install a
production service, retain secrets, activate future tasks, or update the
candidate distribution lock.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

PROFILE = "pantheon-governed"
ADMISSION_ID = "admission-hermes-020-lab"
PROFILE_KEY = "hermes-profile-lab-key"
DEFAULT_KEY = "hermes-default-lab-key"
PANTHEON_KEY = "pantheon-lab-key"
EXPECTED_TOOLS = {"pantheon_context_manifest", "pantheon_context_entity"}
EXPECTED_COMPONENTS = {"run-binding", "context-bridge", "runtime-observer"}
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class LabAcceptanceError(RuntimeError):
    pass


def _write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _write_env(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = "".join(f"{key}={value}\n" for key, value in values.items())
    path.write_text(rendered, encoding="utf-8")
    path.chmod(0o600)


def configure(hermes_home: Path, fixture_url: str) -> dict[str, Any]:
    """Write an isolated multiplexed default/profile configuration."""

    hermes_home = hermes_home.resolve()
    profile_home = hermes_home / "profiles" / PROFILE
    if not profile_home.is_dir():
        raise LabAcceptanceError(
            f"profile directory does not exist; run Hermes profile create first: {profile_home}"
        )

    memory_off = {
        "provider": "",
        "memory_enabled": False,
        "user_profile_enabled": False,
    }
    _write_yaml(
        hermes_home / "config.yaml",
        {
            "gateway": {"multiplex_profiles": True},
            "memory": dict(memory_off),
            "platform_toolsets": {"api_server": [], "cli": []},
            "plugins": {"enabled": [], "disabled": []},
        },
    )
    _write_env(
        hermes_home / ".env",
        {
            "API_SERVER_ENABLED": "true",
            "API_SERVER_KEY": DEFAULT_KEY,
        },
    )

    # Hermes 0.20 evaluates the built-in memory tool independently for each
    # platform. ``hermes memory status`` resolves the ``cli`` surface, while
    # the governed Runs API resolves ``api_server``. Both are therefore
    # explicit and limited to the same reviewed plugin toolset; neither may
    # inherit the default ``hermes-cli`` composite that contains ``memory``.
    governed_toolsets = ["pantheon_context"]
    _write_yaml(
        profile_home / "config.yaml",
        {
            "model": {
                "provider": "custom",
                "default": "lab-model",
                "base_url": fixture_url.rstrip("/") + "/v1",
                "api_mode": "chat_completions",
            },
            "memory": dict(memory_off),
            "platform_toolsets": {
                "api_server": list(governed_toolsets),
                "cli": list(governed_toolsets),
            },
            "plugins": {
                "enabled": ["pantheon-context-bridge"],
                "disabled": [],
            },
        },
    )
    _write_env(
        profile_home / ".env",
        {
            "API_SERVER_KEY": PROFILE_KEY,
            "PANTHEON_HERMES_API_BASE": fixture_url.rstrip("/"),
            "PANTHEON_HERMES_API_KEY": PANTHEON_KEY,
            "OPENAI_API_KEY": "local-lab-provider-key",
        },
    )

    return {
        "kind": "hermes_020_lab_configuration",
        "hermes_home": str(hermes_home),
        "profile": PROFILE,
        "multiplex_profiles": True,
        "profile_api_prefix": f"/p/{PROFILE}",
        "platform_toolsets_expected": {
            "api_server": list(governed_toolsets),
            "cli": list(governed_toolsets),
        },
        "memory_axes_expected": {
            "external_provider": "off",
            "built_in_memory_injection": "off",
            "built_in_user_profile_injection": "off",
            "memory_tool": "off",
            "session_memory_key": "absent",
        },
        "expected_tools": sorted(EXPECTED_TOOLS),
        "production_activation": False,
        "future_task_authorization": False,
    }


def _request_json(url: str, *, bearer: str | None = None) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=5) as response:  # nosec B310: lab loopback URLs only
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise LabAcceptanceError(f"{url} did not return an object")
    return payload


def wait_http(url: str, bearer: str | None, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error = "not attempted"
    while time.monotonic() < deadline:
        try:
            return _request_json(url, bearer=bearer)
        except (HTTPError, URLError, OSError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            time.sleep(0.5)
    raise LabAcceptanceError(f"HTTP surface did not become ready: {url}: {last_error}")


def wait_run(base_url: str, api_key: str, run_id: str, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = _request_json(
            base_url.rstrip("/") + f"/v1/runs/{run_id}",
            bearer=api_key,
        )
        if str(last.get("status") or "").lower() in {"completed", "failed", "cancelled"}:
            return last
        time.sleep(0.5)
    raise LabAcceptanceError(f"Hermes run did not reach a terminal state: {last}")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LabAcceptanceError(f"cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LabAcceptanceError(f"{path} must contain an object")
    return value


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LabAcceptanceError(message)


def validate(artifacts: Path) -> dict[str, Any]:
    artifacts = artifacts.resolve()
    version = (artifacts / "hermes-version.txt").read_text(encoding="utf-8").strip()
    source_artifact_digest = (
        artifacts / "hermes-source-artifact.sha256"
    ).read_text(encoding="utf-8").strip()
    distribution = _load_json(artifacts / "distribution-verification.json")
    memory = _load_json(artifacts / "memory-status-launch.json")
    observation = _load_json(artifacts / "runtime-observation.json")
    launch = _load_json(artifacts / "launch-receipt.json")
    terminal = _load_json(artifacts / "run-terminal.json")
    reconciliation = _load_json(artifacts / "return-receipt.json")
    fixture_state = _load_json(artifacts / "fixture-state.json")
    rollback = _load_json(artifacts / "rollback.json")

    _require("0.20.0" in version, f"unexpected Hermes version: {version}")
    _require(
        SHA256_RE.fullmatch(source_artifact_digest) is not None,
        "source artifact digest is invalid",
    )
    _require(
        distribution.get("status") == "candidate",
        "distribution lock was not verified as candidate",
    )
    components = distribution.get("components") or []
    _require(
        {str(item.get("component_id")) for item in components if isinstance(item, dict)}
        == EXPECTED_COMPONENTS,
        "verified distribution component identities differ from the standard composition",
    )
    _require(
        distribution.get("verified_component_digest_count") == 3,
        "not all standard component digests were verified",
    )
    _require(
        distribution.get("authority_effect") == "none",
        "distribution verification reported an authority effect",
    )

    _require(memory.get("status") == "qualified", "fresh launch memory receipt is not qualified")
    for key in (
        "external_provider",
        "built_in_memory_injection",
        "built_in_user_profile_injection",
        "memory_tool",
    ):
        _require(memory.get(key) == "off", f"memory axis is active or unknown: {key}")
    _require(memory.get("raw_output_retained") is False, "raw memory output was retained")

    _require(observation.get("runs_api_status") == "compatible", "Runs API is not compatible")
    _require(observation.get("safety_status") == "qualified", "runtime posture is not qualified")
    _require(
        observation.get("profile_surface", {}).get("observed_profile") == PROFILE,
        "wrong profile route observed",
    )
    _require(
        observation.get("memory_posture", {}).get("status") == "qualified",
        "memory posture is not qualified",
    )
    tool_surface = observation.get("tool_surface") or {}
    _require(
        set(tool_surface.get("active_tools") or []) == EXPECTED_TOOLS,
        "unexpected active Hermes tools",
    )
    _require(observation.get("session_memory_header_sent") is False, "observer sent a memory header")

    _require(launch.get("runtime_submission_performed") is True, "Hermes run was not submitted")
    _require(launch.get("runtime_start_recorded") is True, "Pantheon start was not recorded")
    _require(launch.get("session_id") == ADMISSION_ID, "launch session/admission correlation failed")
    _require(launch.get("session_memory_header_sent") is False, "launch sent a memory header")
    _require(launch.get("automatic_retry_performed") is False, "launch retried automatically")
    _require(launch.get("provider_routing_performed") is False, "binding routed a provider")
    _require(launch.get("model_override_performed") is False, "binding overrode the model")

    _require(terminal.get("status") == "completed", f"Hermes run did not complete: {terminal}")
    _require(
        "LAB_ACCEPTANCE_COMPLETED" in str(terminal.get("output") or ""),
        "synthetic run did not complete the context checks",
    )

    _require(reconciliation.get("pantheon_return_recorded") is True, "Pantheon return was not recorded")
    _require(
        reconciliation.get("technical_receipt_is_evidence") is False,
        "technical receipt was misclassified as Evidence",
    )
    _require(reconciliation.get("scheduler_effect") is False, "reconciliation introduced scheduler effect")
    _require(reconciliation.get("retry_effect") is False, "reconciliation introduced retry effect")
    recorded = reconciliation.get("recorded") or {}
    _require(recorded.get("result_accepted") is False, "fixture accepted the runtime result")
    _require(recorded.get("evidence_admitted") is False, "fixture admitted Evidence")
    _require(recorded.get("project_mutated") is False, "fixture mutated a Project")

    reads = fixture_state.get("pantheon_reads") or []
    _require(any(path.endswith("/active-context") for path in reads), "manifest was not read")
    _require(any(path.endswith("/project/project-lab") for path in reads), "admitted entity was not read")
    _require(
        any(path.endswith("/project/project-outside") for path in reads),
        "outside entity refusal was not exercised",
    )
    _require(
        int(fixture_state.get("provider_calls") or 0) >= 4,
        "model loop did not exercise all tool steps",
    )

    journal_path = artifacts / "fixture-journal.jsonl"
    journal = [
        json.loads(line)
        for line in journal_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    _require(journal, "fixture journal is empty")
    _require(
        not any(item.get("session_memory_header_present") for item in journal),
        "X-Hermes-Session-Key was observed by a lab service",
    )

    _require(rollback.get("plugin_disabled") is True, "plugin rollback was not verified")
    _require(rollback.get("gateway_stopped") is True, "gateway rollback was not verified")
    _require(
        rollback.get("profile_route_unreachable") is True,
        "profile route remained reachable after rollback",
    )

    summary = {
        "kind": "hermes_020_ephemeral_lab_acceptance",
        "status": "passed",
        "hermes_version": "0.20.0",
        "source_artifact_digest": source_artifact_digest,
        "profile": PROFILE,
        "profile_route": f"/p/{PROFILE}",
        "distribution_components": sorted(EXPECTED_COMPONENTS),
        "tool_surface": sorted(EXPECTED_TOOLS),
        "memory_posture": "qualified_off",
        "synthetic_run_completed": True,
        "context_manifest_read": True,
        "admitted_entity_read": True,
        "outside_entity_refused": True,
        "rollback_verified": True,
        "target_installation_observed": False,
        "production_activated": False,
        "future_tasks_authorized": False,
        "result_accepted": False,
        "evidence_admitted": False,
        "limits": [
            "This qualifies an ephemeral GitHub-hosted laboratory installation only.",
            "The agency/NAS installation, OpenWebUI configuration and production rollback remain unobserved.",
            "The inference provider and Pantheon API were deterministic local fixtures.",
        ],
    }
    (artifacts / "acceptance-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    cfg = sub.add_parser("configure")
    cfg.add_argument("--hermes-home", type=Path, required=True)
    cfg.add_argument("--fixture-url", required=True)
    cfg.add_argument("--output", type=Path)

    wait = sub.add_parser("wait-http")
    wait.add_argument("--url", required=True)
    wait.add_argument("--bearer")
    wait.add_argument("--timeout", type=float, default=60.0)
    wait.add_argument("--output", type=Path)

    run = sub.add_parser("wait-run")
    run.add_argument("--base-url", required=True)
    run.add_argument("--api-key", required=True)
    run.add_argument("--run-id", required=True)
    run.add_argument("--timeout", type=float, default=120.0)
    run.add_argument("--output", type=Path, required=True)

    check = sub.add_parser("validate")
    check.add_argument("--artifacts", type=Path, required=True)

    return parser


def _emit(payload: dict[str, Any], output: Path | None) -> None:
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if output is None:
        print(rendered, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "configure":
        _emit(configure(args.hermes_home, args.fixture_url), args.output)
        return 0
    if args.command == "wait-http":
        _emit(wait_http(args.url, args.bearer, args.timeout), args.output)
        return 0
    if args.command == "wait-run":
        _emit(wait_run(args.base_url, args.api_key, args.run_id, args.timeout), args.output)
        return 0
    if args.command == "validate":
        _emit(validate(args.artifacts), None)
        return 0
    raise LabAcceptanceError(f"unknown command: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except LabAcceptanceError as exc:
        print(f"Hermes 0.20 lab acceptance refused: {exc}")
        raise SystemExit(1) from exc