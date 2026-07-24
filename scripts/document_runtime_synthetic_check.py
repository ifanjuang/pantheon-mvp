#!/usr/bin/env python3
"""Operator-run synthetic verification for the document runtime vertical.

Default mode is read-only. The optional intake mode is deliberately restricted to
an explicitly synthetic Task Contract and uses the installed Hermes skill's
transport script. It never uploads/deletes Paperless sources, publishes Knowledge,
admits Evidence, mutates Paperless metadata or changes activation state.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class CheckError(RuntimeError):
    pass


def _json_request(
    method: str,
    url: str,
    *,
    bearer: str,
    body: dict[str, Any] | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json", "Authorization": f"Bearer {bearer}"}
    if body is not None:
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise CheckError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise CheckError(f"unreachable {url}: {exc}") from exc
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CheckError(f"invalid JSON from {url}") from exc
    if not isinstance(value, dict):
        raise CheckError(f"expected JSON object from {url}")
    return value


def _index_observations(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["source"]: item
        for item in payload.get("observations", [])
        if isinstance(item, dict) and isinstance(item.get("source"), str)
    }


def assess_observations(payload: dict[str, Any]) -> dict[str, Any]:
    observed = _index_observations(payload)
    checks = {
        "paperless_source_path": (
            observed.get("paperless_gateway", {}).get("paperless_reachability_status")
            == "reachable"
        ),
        "pantheon_pdp_ready": (
            observed.get("pantheon_pdp", {}).get("readiness_status") == "ready_observed"
        ),
        "docling_health_endpoint": (
            observed.get("docling_serve", {}).get("reachability_status") == "reachable"
        ),
        "hermes_skill_installed": (
            observed.get("hermes_native_inventory", {}).get("installation_status")
            == "installed_observed"
        ),
    }
    return {
        "checks": checks,
        "candidate_ready_for_synthetic_intake": all(checks.values()),
        "meaning": "transport_and_runtime_prerequisites_only",
        "safety_status": "not_inferred",
        "production_authorization": False,
    }


def _skill_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    hermes_home = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()
    return (hermes_home / "skills" / "pantheon-document-intake").resolve()


def _run_skill_json(
    skill_root: Path,
    args: list[str],
    *,
    timeout: float = 120.0,
    runner=subprocess.run,
) -> dict[str, Any]:
    script = skill_root / "scripts" / "pantheon_document_intake.py"
    if not script.is_file():
        raise CheckError(f"installed skill transport script not found: {script}")
    try:
        completed = runner(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CheckError(f"cannot execute installed skill transport: {exc}") from exc
    if int(completed.returncode) != 0:
        raise CheckError(
            "installed skill transport failed: "
            + (completed.stderr or completed.stdout or "no diagnostic")[:2000]
        )
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CheckError("installed skill transport returned invalid JSON") from exc
    if not isinstance(value, dict):
        raise CheckError("installed skill transport must return a JSON object")
    return value


def _assert_synthetic_contract(contract_path: Path, source_ref: str) -> str:
    try:
        text = contract_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CheckError(f"cannot read Task Contract: {exc}") from exc
    lowered = text.lower()
    if "synthetic" not in lowered:
        raise CheckError(
            "refusing intake: Task Contract must be explicitly synthetic (contain 'synthetic')"
        )
    if source_ref not in text:
        raise CheckError(
            "refusing intake: exact Paperless source_ref is not present in the synthetic Task Contract"
        )
    return text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Observe the document runtime stack and optionally verify one synthetic intake."
    )
    parser.add_argument(
        "--observer-url",
        default=os.environ.get(
            "PANTHEON_DOCUMENT_RUNTIME_OBSERVER_URL", "http://document-runtime-observer:8083"
        ),
    )
    parser.add_argument(
        "--cockpit-key",
        default=os.environ.get("MVP_COCKPIT_API_KEY", ""),
        help="Prefer MVP_COCKPIT_API_KEY environment variable; do not put secrets in shell history.",
    )
    parser.add_argument("--run-intake", action="store_true")
    parser.add_argument("--ack", default="")
    parser.add_argument("--skill-root")
    parser.add_argument("--document-id", type=int)
    parser.add_argument("--version-id")
    parser.add_argument("--contract")
    parser.add_argument("--decision")
    parser.add_argument("--ingestion-id", default="synthetic-document-runtime-check")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if not args.cockpit_key:
            raise CheckError("MVP_COCKPIT_API_KEY is required for the read-only observer")
        observer_url = args.observer_url.rstrip("/")
        observations = _json_request(
            "GET",
            f"{observer_url}/v1/document-runtime/observations",
            bearer=args.cockpit_key,
        )
        assessment = assess_observations(observations)
        receipt: dict[str, Any] = {
            "object_type": "synthetic_document_runtime_check_receipt",
            "synthetic": True,
            "observations": observations,
            "assessment": assessment,
            "intake_attempted": False,
            "technical_receipt_is_evidence": False,
            "human_issuer_authentication_proven": False,
            "activation_changed": False,
            "production_authorization": False,
        }

        if args.run_intake:
            if args.ack != "SYNTHETIC_ONLY":
                raise CheckError("--run-intake requires --ack SYNTHETIC_ONLY")
            if not assessment["candidate_ready_for_synthetic_intake"]:
                raise CheckError("runtime observations are not ready for a synthetic intake attempt")
            missing = [
                name
                for name, value in (
                    ("--document-id", args.document_id),
                    ("--version-id", args.version_id),
                    ("--contract", args.contract),
                    ("--decision", args.decision),
                )
                if value in (None, "")
            ]
            if missing:
                raise CheckError("missing synthetic intake arguments: " + ", ".join(missing))
            if not os.environ.get("MVP_HERMES_API_KEY", "").strip():
                raise CheckError("MVP_HERMES_API_KEY must be present in the operator environment")

            root = _skill_root(args.skill_root)
            capture = _run_skill_json(
                root,
                [
                    "capture",
                    "--document-id",
                    str(args.document_id),
                    "--version-id",
                    str(args.version_id),
                ],
            )
            source_ref = str(capture.get("source_ref") or "")
            if not source_ref:
                raise CheckError("exact capture returned no source_ref")
            _assert_synthetic_contract(Path(args.contract), source_ref)

            intake_args = [
                "intake",
                "--document-id",
                str(args.document_id),
                "--version-id",
                str(args.version_id),
                "--contract",
                str(Path(args.contract)),
                "--decision",
                str(Path(args.decision)),
                "--ingestion-id",
                str(args.ingestion_id),
            ]
            result = _run_skill_json(root, intake_args)
            receipt.update(
                {
                    "intake_attempted": True,
                    "source_capture": {
                        key: capture.get(key)
                        for key in (
                            "document_id",
                            "version_id",
                            "original_filename",
                            "content_hash",
                            "storage_reference",
                            "source_ref",
                        )
                    },
                    "intake_result": result,
                    "knowledge_published": bool(result.get("knowledge_published", False)),
                    "evidence_admitted": bool(result.get("evidence_admitted", False)),
                    "agent_skill_selection_proven": False,
                }
            )

        json.dump(receipt, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        if args.run_intake:
            return 0 if receipt.get("intake_result", {}).get("status") == "applied" else 4
        return 0 if assessment["candidate_ready_for_synthetic_intake"] else 3
    except CheckError as exc:
        print(f"document-runtime-synthetic-check: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
