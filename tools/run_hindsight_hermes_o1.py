#!/usr/bin/env python3
"""Bounded O1 harness for Hermes assistant-personal + Hindsight.

This harness configures an isolated Hermes profile against an already-running
Hindsight endpoint. It does not install Hindsight, write Pantheon state, admit
Evidence, or alter the governed profile.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import yaml

ASSISTANT_PROFILE = "assistant-personal"
GOVERNED_PROFILE = "pantheon-governed"
DEFAULT_BANK = "pantheon-o1-synthetic"
MARKER = "PANTHEON_O1_SYNTHETIC_MEMORY_MARKER"


class O1Error(RuntimeError):
    pass


def _write_yaml(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_env(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{k}={v}\n" for k, v in values.items() if v), encoding="utf-8")
    path.chmod(0o600)


def configure(
    hermes_home: Path,
    *,
    hindsight_api_url: str,
    hindsight_api_key: str,
    provider_url: str,
    bank_id: str,
) -> dict[str, Any]:
    hermes_home = hermes_home.resolve()
    profile_home = hermes_home / "profiles" / ASSISTANT_PROFILE
    governed_home = hermes_home / "profiles" / GOVERNED_PROFILE
    if not profile_home.is_dir() or not governed_home.is_dir():
        raise O1Error("assistant-personal and pantheon-governed profiles must exist")

    _write_yaml(
        profile_home / "config.yaml",
        {
            "model": {
                "provider": "custom",
                "default": "o1-lab-model",
                "base_url": provider_url.rstrip("/") + "/v1",
                "api_mode": "chat_completions",
            },
            "memory": {
                "provider": "hindsight",
                "memory_enabled": False,
                "user_profile_enabled": False,
            },
            "platform_toolsets": {"cli": []},
        },
    )
    _write_json(
        profile_home / "hindsight" / "config.json",
        {
            "mode": "cloud",
            "api_url": hindsight_api_url.rstrip("/"),
            "bank_id": bank_id,
            "memory_mode": "tools",
            "auto_retain": False,
            "auto_recall": False,
            "retain_async": False,
            "recall_budget": "low",
        },
    )
    _write_env(
        profile_home / ".env",
        {
            "OPENAI_API_KEY": "local-o1-provider-key",
            "HINDSIGHT_API_URL": hindsight_api_url.rstrip("/"),
            "HINDSIGHT_API_KEY": hindsight_api_key,
            "HINDSIGHT_BANK_ID": bank_id,
            "HINDSIGHT_AUTO_RETAIN": "false",
            "HINDSIGHT_AUTO_RECALL": "false",
        },
    )

    # O1 never rewrites the governed profile. Its posture is observed separately.
    return {
        "kind": "hindsight_hermes_o1_configuration",
        "assistant_profile": ASSISTANT_PROFILE,
        "governed_profile": GOVERNED_PROFILE,
        "bank_id": bank_id,
        "memory_provider": "hindsight",
        "memory_mode": "tools",
        "auto_retain": False,
        "auto_recall": False,
        "conversation_retention": "off",
        "pantheon_write_path": False,
        "evidence_admission": False,
        "production_activation": False,
    }


def validate(artifacts: Path) -> dict[str, Any]:
    artifacts = artifacts.resolve()
    assistant_status = (artifacts / "assistant-memory-status.txt").read_text(encoding="utf-8")
    governed = json.loads((artifacts / "governed-memory-status.json").read_text(encoding="utf-8"))
    direct_recall = json.loads((artifacts / "direct-recall.json").read_text(encoding="utf-8"))
    hermes_output = (artifacts / "hermes-output.txt").read_text(encoding="utf-8")
    rollback = json.loads((artifacts / "rollback.json").read_text(encoding="utf-8"))

    if "hindsight" not in assistant_status.lower():
        raise O1Error("assistant-personal did not report Hindsight as selected provider")
    if governed.get("status") != "qualified" or governed.get("active_axes") != []:
        raise O1Error("pantheon-governed memory posture is not still fully off")
    if MARKER not in json.dumps(direct_recall, ensure_ascii=False):
        raise O1Error("direct Hindsight recall did not return the synthetic marker")
    if "O1_HINDSIGHT_RECALL_COMPLETED" not in hermes_output:
        raise O1Error("Hermes did not complete a Hindsight recall tool cycle")
    if rollback.get("assistant_profile_removed") is not True:
        raise O1Error("assistant-personal sandbox profile was not removed")

    summary = {
        "kind": "hindsight_hermes_o1_acceptance",
        "status": "passed",
        "assistant_profile": ASSISTANT_PROFILE,
        "governed_profile": GOVERNED_PROFILE,
        "hindsight_bank": DEFAULT_BANK,
        "direct_recall_verified": True,
        "hermes_recall_verified": True,
        "conversation_retention": "off",
        "governed_memory_posture": "qualified_off",
        "pantheon_state_mutated": False,
        "evidence_admitted": False,
        "production_activated": False,
        "rollback_verified": True,
    }
    _write_json(artifacts / "acceptance-summary.json", summary)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    cfg = sub.add_parser("configure")
    cfg.add_argument("--hermes-home", type=Path, required=True)
    cfg.add_argument("--hindsight-api-url", required=True)
    cfg.add_argument("--hindsight-api-key", default="")
    cfg.add_argument("--provider-url", required=True)
    cfg.add_argument("--bank-id", default=DEFAULT_BANK)
    cfg.add_argument("--output", type=Path, required=True)
    val = sub.add_parser("validate")
    val.add_argument("--artifacts", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "configure":
        result = configure(
            args.hermes_home,
            hindsight_api_url=args.hindsight_api_url,
            hindsight_api_key=args.hindsight_api_key,
            provider_url=args.provider_url,
            bank_id=args.bank_id,
        )
        _write_json(args.output, result)
        return 0
    if args.command == "validate":
        print(json.dumps(validate(args.artifacts), indent=2, sort_keys=True))
        return 0
    raise O1Error(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
