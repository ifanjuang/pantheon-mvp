#!/usr/bin/env python3
"""Audit Pantheon-Next and pantheon-mvp as one architecture.

Report-only. Findings are review candidates, never automatic deletion proof.
The audit checks ownership placement, generation/version naming, duplicate schema
identities, duplicate active filenames, legacy/compatibility markers and Python
module structure across both repositories.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

TEXT_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json", ".toml", ".sql", ".js", ".css", ".html"}
EXCLUDED_PARTS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache"}
VERSION_TOKEN = re.compile(r"(?:^|[_./-])v(?:0|1|2|3|\d+)(?:$|[_./-])", re.IGNORECASE)
LEGACY_TOKEN = re.compile(r"(?:^|[_./-])(legacy|compat|deprecated|obsolete|archive|old)(?:$|[_./-])", re.IGNORECASE)
SCHEMA_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    repository: str
    path: str
    detail: str


@dataclass(frozen=True)
class RepositorySummary:
    repository: str
    files: int
    python_files: int
    schemas: int
    findings: int


def iter_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in TEXT_SUFFIXES
        and not any(part in EXCLUDED_PARTS for part in path.parts)
    )


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def schema_identity(path: Path, text: str) -> str | None:
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        value = payload.get("$id") or payload.get("schema_id")
        return value if isinstance(value, str) else None
    if path.suffix.lower() in {".yaml", ".yml"}:
        for line in text.splitlines()[:80]:
            stripped = line.strip()
            if stripped.startswith("$id:") or stripped.startswith("schema_id:"):
                return stripped.split(":", 1)[1].strip().strip("'\"") or None
    return None


def python_symbols(path: Path, text: str) -> set[str]:
    if path.suffix.lower() != ".py":
        return set()
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return set()
    return {
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    }


def expected_owner(relative: str) -> str | None:
    normalized = relative.lower()
    if normalized.startswith(("schemas/", "docs/governance/", "docs/domain-packs/", "mcp-server/")):
        return "Pantheon-Next"
    if normalized.startswith(("mvp_vertical/", "openwebui/", "scripts/", "tools/", "tests/")):
        return "pantheon-mvp"
    return None


def audit_repository(name: str, root: Path) -> tuple[list[Finding], dict[str, list[str]], dict[str, list[str]], set[str]]:
    findings: list[Finding] = []
    schemas: dict[str, list[str]] = defaultdict(list)
    basenames: dict[str, list[str]] = defaultdict(list)
    symbols: set[str] = set()

    for path in iter_files(root):
        relative = path.relative_to(root).as_posix()
        text = read_text(path)
        lower = relative.lower()
        basenames[path.name.lower()].append(relative)
        symbols.update(python_symbols(path, text))

        if VERSION_TOKEN.search(relative):
            findings.append(Finding("generation_name", "high", name, relative, "path contains a generation/version token"))
        if LEGACY_TOKEN.search(relative):
            findings.append(Finding("legacy_path", "medium", name, relative, "path advertises legacy/compatibility/obsolete status"))

        owner = expected_owner(relative)
        if owner and owner != name:
            findings.append(Finding("ownership_mismatch", "high", name, relative, f"path convention belongs to {owner}"))

        identity = schema_identity(path, text)
        if identity:
            schemas[identity].append(relative)
            if not SCHEMA_ID.match(identity):
                findings.append(Finding("unstable_schema_id", "medium", name, relative, f"schema identity is not stable: {identity}"))
            if VERSION_TOKEN.search(identity):
                findings.append(Finding("versioned_schema_id", "high", name, relative, f"schema identity contains a version token: {identity}"))

        if path.suffix.lower() in {".py", ".js", ".md"}:
            marker_count = sum(text.lower().count(token) for token in ("legacy", "compatibility", "deprecated", "obsolete"))
            if marker_count >= 4:
                findings.append(Finding("compatibility_density", "medium", name, relative, f"contains {marker_count} compatibility/legacy markers"))

        if name == "Pantheon-Next" and lower.startswith("mvp_vertical/"):
            findings.append(Finding("runtime_in_governance_repo", "critical", name, relative, "executable MVP implementation is misplaced in governance repository"))
        if name == "pantheon-mvp" and lower.startswith("docs/governance/"):
            findings.append(Finding("doctrine_in_runtime_repo", "high", name, relative, "governance doctrine should be owned by Pantheon-Next"))

    for identity, paths in schemas.items():
        if len(paths) > 1:
            for path in paths:
                findings.append(Finding("duplicate_schema_identity", "critical", name, path, f"schema identity {identity} occurs {len(paths)} times"))

    for basename, paths in basenames.items():
        if len(paths) > 1 and basename not in {"__init__.py", "readme.md", "index.md"}:
            for path in paths:
                findings.append(Finding("duplicate_filename", "low", name, path, f"filename {basename} occurs {len(paths)} times; review responsibility overlap"))

    return findings, schemas, basenames, symbols


def audit_cross_repo(next_root: Path, mvp_root: Path) -> tuple[list[Finding], list[RepositorySummary]]:
    all_findings: list[Finding] = []
    data = {}
    for name, root in (("Pantheon-Next", next_root), ("pantheon-mvp", mvp_root)):
        findings, schemas, basenames, symbols = audit_repository(name, root)
        all_findings.extend(findings)
        files = iter_files(root)
        data[name] = (schemas, basenames, symbols, files, findings)

    next_schemas, _, next_symbols, next_files, next_findings = data["Pantheon-Next"]
    mvp_schemas, _, mvp_symbols, mvp_files, mvp_findings = data["pantheon-mvp"]

    for identity in sorted(set(next_schemas) & set(mvp_schemas)):
        for path in mvp_schemas[identity]:
            all_findings.append(Finding(
                "vendored_schema_overlap", "info", "pantheon-mvp", path,
                f"schema {identity} also exists in Pantheon-Next; must remain pinned/vendor-derived, never independently authoritative",
            ))

    generic = {"main", "run", "create", "update", "load", "validate", "get", "list"}
    for symbol in sorted((next_symbols & mvp_symbols) - generic):
        all_findings.append(Finding(
            "cross_repo_symbol_overlap", "low", "cross-repo", symbol,
            "public Python symbol exists in both repositories; verify governance/implementation ownership",
        ))

    summaries = [
        RepositorySummary("Pantheon-Next", len(next_files), sum(p.suffix == ".py" for p in next_files), len(next_schemas), len(next_findings)),
        RepositorySummary("pantheon-mvp", len(mvp_files), sum(p.suffix == ".py" for p in mvp_files), len(mvp_schemas), len(mvp_findings)),
    ]
    return sorted(all_findings, key=lambda f: (f.severity, f.repository, f.path, f.code)), summaries


def render_markdown(findings: Iterable[Finding], summaries: Iterable[RepositorySummary]) -> str:
    findings = list(findings)
    lines = [
        "# Pantheon architecture inventory",
        "",
        "> Cross-repository, report-only audit. A finding is not deletion proof.",
        "",
        "## Repositories",
        "",
    ]
    for summary in summaries:
        lines.append(
            f"- **{summary.repository}**: {summary.files} scanned files, "
            f"{summary.python_files} Python files, {summary.schemas} schema identities, {summary.findings} local findings"
        )
    lines.extend(["", "## Findings", ""])
    if not findings:
        lines.append("None detected.")
    for finding in findings:
        lines.append(f"- **{finding.severity} · {finding.code}** — `{finding.repository}:{finding.path}` — {finding.detail}")
    lines.extend([
        "",
        "## Classification rule",
        "",
        "Every finding must end as: keep, simplify, merge, move, deprecate, delete, or uncertain.",
        "Deletion requires proof from imports, routes, packaging, tests, deployment and active doctrine.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pantheon-next-root", type=Path, required=True)
    parser.add_argument("--pantheon-mvp-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-critical", action="store_true")
    args = parser.parse_args()

    findings, summaries = audit_cross_repo(args.pantheon_next_root.resolve(), args.pantheon_mvp_root.resolve())
    rendered = (
        json.dumps({"summaries": [asdict(s) for s in summaries], "findings": [asdict(f) for f in findings]}, indent=2, sort_keys=True) + "\n"
        if args.format == "json" else render_markdown(findings, summaries)
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if args.fail_on_critical and any(f.severity == "critical" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
