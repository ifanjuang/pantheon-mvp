#!/usr/bin/env python3
"""Cross-repository architecture audit for Pantheon-Next and pantheon-mvp.

Report-only. Findings are review candidates, never automatic deletion or
ownership decisions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

ARCHITECTURE_SUFFIXES = {
    ".py", ".json", ".yaml", ".yml", ".md", ".sql", ".js", ".css",
    ".html", ".toml", ".sh",
}
EXCLUDED_PARTS = {
    ".git", ".pytest_cache", ".venv", "venv", "__pycache__", "node_modules",
    "vendor", "dist", "build",
}
GENERATION_TOKEN = re.compile(r"(?:^|[_./-])v(?:0|1|2|3)(?:$|[_./-])", re.IGNORECASE)
AUTHORITY_OWNERS = {
    "evidence": "Pantheon-Next",
    "change_candidate": "Pantheon-Next",
    "capability_slot": "Pantheon-Next",
    "project_claim": "Pantheon-Next",
    "execution_admission": "Pantheon-Next",
    "task_contract": "Pantheon-Next",
    "context_pack": "Pantheon-Next",
    "cockpit": "pantheon-mvp",
    "postgres": "pantheon-mvp",
    "paperless": "pantheon-mvp",
    "docling": "pantheon-mvp",
    "hermes": "Hermes/external runtime",
}


@dataclass(frozen=True)
class RepositorySpec:
    name: str
    role: str
    root: Path


@dataclass(frozen=True)
class Artifact:
    repository: str
    path: str
    suffix: str
    stem: str
    lines: int
    digest: str
    generation_named: bool
    authority_terms: tuple[str, ...]


def repository_spec(value: str) -> RepositorySpec:
    try:
        name, role, raw_root = value.split("=", 2)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected NAME=ROLE=PATH") from exc
    root = Path(raw_root).expanduser().resolve()
    if not root.is_dir():
        raise argparse.ArgumentTypeError(f"repository root does not exist: {root}")
    return RepositorySpec(name=name, role=role, root=root)


def iter_artifacts(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in ARCHITECTURE_SUFFIXES
        and not any(part in EXCLUDED_PARTS for part in path.parts)
    )


def inspect_artifact(spec: RepositorySpec, path: Path) -> Artifact:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    relative = path.relative_to(spec.root).as_posix()
    lowered = text.lower()
    return Artifact(
        repository=spec.name,
        path=relative,
        suffix=path.suffix.lower(),
        stem=path.stem.lower(),
        lines=len(text.splitlines()),
        digest=hashlib.sha256(raw).hexdigest(),
        generation_named=bool(GENERATION_TOKEN.search(relative)),
        authority_terms=tuple(sorted(term for term in AUTHORITY_OWNERS if term in lowered)),
    )


def build_inventory(specs: list[RepositorySpec]) -> list[Artifact]:
    return [inspect_artifact(spec, path) for spec in specs for path in iter_artifacts(spec.root)]


def exact_duplicates(records: list[Artifact]) -> list[list[Artifact]]:
    groups: dict[str, list[Artifact]] = defaultdict(list)
    for record in records:
        groups[record.digest].append(record)
    return [sorted(group, key=lambda item: (item.repository, item.path))
            for group in groups.values() if len(group) > 1]


def repeated_stems(records: list[Artifact]) -> list[list[Artifact]]:
    groups: dict[str, list[Artifact]] = defaultdict(list)
    for record in records:
        if record.stem not in {"readme", "index", "__init__"}:
            groups[record.stem].append(record)
    return [sorted(group, key=lambda item: (item.repository, item.path))
            for group in groups.values() if len({item.repository for item in group}) > 1]


def authority_collisions(records: list[Artifact]) -> dict[str, list[Artifact]]:
    result: dict[str, list[Artifact]] = {}
    for term, owner in AUTHORITY_OWNERS.items():
        matches = [record for record in records if term in record.authority_terms]
        if len({record.repository for record in matches}) > 1:
            result[f"{term} (canonical owner: {owner})"] = sorted(
                matches, key=lambda item: (item.repository, item.path)
            )
    return result


def render_markdown(specs: list[RepositorySpec], records: list[Artifact]) -> str:
    versioned = [record for record in records if record.generation_named]
    duplicates = exact_duplicates(records)
    stems = repeated_stems(records)
    collisions = authority_collisions(records)
    lines = [
        "# Pantheon cross-repository architecture inventory", "",
        "> Report-only: findings require human review and are not deletion proof.",
        "", "## Repositories", "",
    ]
    lines.extend(f"- **{spec.name}** — {spec.role} — `{spec.root}`" for spec in specs)
    lines.extend([
        "", "## Summary", "",
        f"- Architecture artifacts: **{len(records)}**",
        f"- Generation-named paths: **{len(versioned)}**",
        f"- Exact duplicate groups: **{len(duplicates)}**",
        f"- Cross-repository repeated names: **{len(stems)}**",
        f"- Authority review groups: **{len(collisions)}**",
        "", "## Generation-named paths", "",
    ])
    lines.extend(f"- `{item.repository}:{item.path}`" for item in versioned)
    if not versioned:
        lines.append("None detected.")
    lines.extend(["", "## Exact duplicates", ""])
    lines.extend("- " + " · ".join(f"`{item.repository}:{item.path}`" for item in group)
                 for group in duplicates)
    if not duplicates:
        lines.append("None detected.")
    lines.extend(["", "## Cross-repository repeated names", ""])
    lines.extend("- " + " · ".join(f"`{item.repository}:{item.path}`" for item in group)
                 for group in stems)
    if not stems:
        lines.append("None detected.")
    lines.extend(["", "## Authority review", ""])
    for label, group in sorted(collisions.items()):
        lines.append(f"- **{label}**")
        lines.extend(f"  - `{item.repository}:{item.path}`" for item in group[:25])
        if len(group) > 25:
            lines.append(f"  - … {len(group) - 25} more")
    if not collisions:
        lines.append("None detected.")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", action="append", type=repository_spec, required=True,
                        help="repeat NAME=ROLE=PATH for pantheon-mvp and Pantheon-Next")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-generation-names", action="store_true")
    args = parser.parse_args()
    records = build_inventory(args.repository)
    rendered = (
        json.dumps({"repositories": [asdict(spec) | {"root": str(spec.root)} for spec in args.repository],
                    "artifacts": [asdict(record) for record in records]}, indent=2, sort_keys=True) + "\n"
        if args.format == "json" else render_markdown(args.repository, records)
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if args.fail_on_generation_names and any(r.generation_named for r in records) else 0


if __name__ == "__main__":
    raise SystemExit(main())
