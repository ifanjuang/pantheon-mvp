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


def test_cross_repo_audit_detects_versioning_duplicates_and_misplacement(tmp_path: Path) -> None:
    tool = _load_tool()
    next_root = tmp_path / "Pantheon-Next"
    mvp_root = tmp_path / "pantheon-mvp"
    (next_root / "schemas").mkdir(parents=True)
    (mvp_root / "mvp_vertical").mkdir(parents=True)
    (mvp_root / "docs" / "governance").mkdir(parents=True)

    (next_root / "schemas" / "project.yaml").write_text("$id: agency.project\ntype: object\n", encoding="utf-8")
    (mvp_root / "mvp_vertical" / "project_v2.py").write_text("class ProjectService: pass\n", encoding="utf-8")
    (mvp_root / "mvp_vertical" / "project.schema.yaml").write_text("$id: agency.project\ntype: object\n", encoding="utf-8")
    (mvp_root / "docs" / "governance" / "AUTHORITY.md").write_text("runtime doctrine\n", encoding="utf-8")

    findings, summaries = tool.audit_cross_repo(next_root, mvp_root)
    codes = {finding.code for finding in findings}

    assert "generation_name" in codes
    assert "vendored_schema_overlap" in codes
    assert "doctrine_in_runtime_repo" in codes
    assert {summary.repository for summary in summaries} == {"Pantheon-Next", "pantheon-mvp"}


def test_schema_identity_duplicate_is_critical(tmp_path: Path) -> None:
    tool = _load_tool()
    root = tmp_path / "repo"
    (root / "schemas").mkdir(parents=True)
    (root / "schemas" / "one.yaml").write_text("$id: duplicate.schema\n", encoding="utf-8")
    (root / "schemas" / "two.yaml").write_text("$id: duplicate.schema\n", encoding="utf-8")

    findings, _, _, _ = tool.audit_repository("Pantheon-Next", root)

    assert any(f.code == "duplicate_schema_identity" and f.severity == "critical" for f in findings)


def test_report_is_deterministic(tmp_path: Path) -> None:
    tool = _load_tool()
    next_root = tmp_path / "next"
    mvp_root = tmp_path / "mvp"
    next_root.mkdir()
    mvp_root.mkdir()
    (next_root / "README.md").write_text("Pantheon\n", encoding="utf-8")
    (mvp_root / "README.md").write_text("MVP\n", encoding="utf-8")

    findings, summaries = tool.audit_cross_repo(next_root, mvp_root)

    assert tool.render_markdown(findings, summaries) == tool.render_markdown(findings, summaries)
    assert "report-only" in tool.render_markdown(findings, summaries).lower()
