from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"
PROJECTION = COCKPIT / "projection" / "project_anatomy_projection.js"
LOADER = COCKPIT / "data" / "cockpit_data_loader.js"
ASSEMBLER = COCKPIT / "projection" / "child_collection_assembler.js"
BOOTSTRAP = COCKPIT / "live_bootstrap.js"


def test_anatomy_projection_remains_read_only_and_does_not_infer_absence() -> None:
    source = PROJECTION.read_text(encoding="utf-8")

    assert 'entity_type: "project_anatomy_projection"' in source
    assert 'entity_type: "apu_object"' in source
    assert 'entity_type: "apu_source_representation"' in source
    assert '"Non mappé ≠ absent"' in source
    assert '"Couverture d’observation non persistée"' in source
    assert '"Hiérarchie non dérivée sans sémantique admise"' in source
    assert "available_actions: []" in source
    assert "fetch(" not in source


def test_data_loader_reads_anatomy_optionally_without_hiding_other_failures() -> None:
    source = LOADER.read_text(encoding="utf-8")

    assert "project-anatomy" in source
    assert "[404, 409]" in source
    assert "projectAnatomy: anatomyPayload?.project_anatomy || null" in source


def test_anatomy_is_loaded_before_child_assembly_and_attached_under_project() -> None:
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
    assembler = ASSEMBLER.read_text(encoding="utf-8")

    anatomy_module = '"projection/project_anatomy_projection.js"'
    assembler_module = '"projection/child_collection_assembler.js"'
    assert bootstrap.index(anatomy_module) < bootstrap.index(assembler_module)
    assert "context.state.projectAnatomy" in assembler
    assert "anatomy.project_ref !== context.selectedProjectId" in assembler
    assert "...assembleAnatomy(context)" in assembler


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required for JS syntax checks")
@pytest.mark.parametrize(
    "path",
    [PROJECTION, LOADER, ASSEMBLER, BOOTSTRAP],
)
def test_anatomy_frontend_javascript_parses(path: Path) -> None:
    subprocess.run(["node", "--check", str(path)], check=True, capture_output=True, text=True)
