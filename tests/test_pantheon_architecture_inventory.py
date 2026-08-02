from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "audit_pantheon_architecture.py"


def _load_tool():
    name = "audit_pantheon_architecture"
    spec = importlib.util.spec_from_file_location(name, TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_cross_repository_audit_detects_duplicates_versions_and_authority(tmp_path: Path) -> None:
    tool = _load_tool()
    next_root = tmp_path / "Pantheon-Next"
    mvp_root = tmp_path / "pantheon-mvp"
    next_root.mkdir()
    mvp_root.mkdir()
    shared = "project_claim and evidence\n"
    (next_root / "project_claim.yaml").write_text(shared, encoding="utf-8")
    (mvp_root / "project_claim.yaml").write_text(shared, encoding="utf-8")
    (mvp_root / "v2_adapter.py").write_text("# cockpit adapter\n", encoding="utf-8")

    specs = [
        tool.RepositorySpec("Pantheon-Next", "governance", next_root),
        tool.RepositorySpec("pantheon-mvp", "implementation", mvp_root),
    ]
    records = tool.build_inventory(specs)

    assert len(tool.exact_duplicates(records)) == 1
    assert len(tool.repeated_stems(records)) == 1
    assert any(record.generation_named for record in records)
    assert "project_claim (canonical owner: Pantheon-Next)" in tool.authority_collisions(records)


def test_cross_repository_report_is_deterministic(tmp_path: Path) -> None:
    tool = _load_tool()
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    (first_root / "alpha.md").write_text("Evidence contract\n", encoding="utf-8")
    (second_root / "alpha.py").write_text("# evidence projection\n", encoding="utf-8")
    specs = [
        tool.RepositorySpec("Pantheon-Next", "governance", first_root),
        tool.RepositorySpec("pantheon-mvp", "implementation", second_root),
    ]
    records = tool.build_inventory(specs)

    assert tool.render_markdown(specs, records) == tool.render_markdown(specs, records)
    assert "Pantheon cross-repository architecture inventory" in tool.render_markdown(specs, records)
