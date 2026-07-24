"""Behavior and boundary checks for the executable Cockpit V2 spatial surface."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"


def _run_node(script: str) -> subprocess.CompletedProcess[str]:
    node = shutil.which("node")
    if node is None:  # pragma: no cover - depends on runner image
        pytest.skip("Node.js is unavailable; JavaScript behavior check skipped")
    return subprocess.run(
        [node, "-e", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("name", ["spatial_navigation.js", "v2_app.js"])
def test_v2_javascript_parses(name: str) -> None:
    node = shutil.which("node")
    if node is None:  # pragma: no cover
        pytest.skip("Node.js is unavailable; JavaScript syntax check skipped")
    result = subprocess.run(
        [node, "--check", str(COCKPIT / name)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_spatial_navigation_keeps_sibling_and_parent_boundaries() -> None:
    script = r'''
      global.window = {};
      require("./mvp_vertical/cockpit/spatial_navigation.js");
      const nav = window.PantheonSpatialNavigation.create({
        root_collection_id: "primary-spaces",
        root_item_ids: ["pantheon", "decisions", "affaires", "knowledge", "tools"],
      });

      nav.selectSibling("affaires");
      if (nav.snapshot().current_id !== "affaires") throw new Error("root selection failed");

      nav.descend({
        parent_entity_id: "affaires",
        collection_id: "projects",
        item_ids: ["lieurey", "trouville", "mannevillette"],
      });
      nav.moveHorizontal(1);
      if (nav.snapshot().current_id !== "trouville") throw new Error("sibling navigation escaped collection");
      if (nav.snapshot().depth !== 1) throw new Error("horizontal navigation changed depth");

      nav.ascend();
      if (nav.snapshot().current_id !== "affaires" || nav.snapshot().depth !== 0) {
        throw new Error("ascend did not restore parent");
      }

      nav.returnToRoot("tools");
      if (nav.snapshot().current_id !== "tools") throw new Error("explicit root jump failed");
    '''
    result = _run_node(script)
    assert result.returncode == 0, result.stderr


def test_v2_route_exposes_five_spaces_and_explicit_navigation() -> None:
    html = (COCKPIT / "v2.html").read_text(encoding="utf-8")
    css = (COCKPIT / "styles" / "v2.css").read_text(encoding="utf-8")
    javascript = (COCKPIT / "v2_app.js").read_text(encoding="utf-8")

    for space in ("pantheon", "decisions", "affaires", "connaissances", "outils"):
        assert f'data-space="{space}"' in html

    assert 'id="v2-previous"' in html
    assert 'id="v2-next"' in html
    assert 'id="v2-descend"' in html
    assert 'id="v2-ascend"' in html
    assert 'id="v2-flip"' in html
    assert 'id="v2-breadcrumb"' in html
    assert 'class="v2-hermes-dock"' in html
    assert 'src="spatial_navigation.js"' in html
    assert 'src="v2_app.js"' in html

    assert '[data-family="project"]' in css
    assert '[data-family="document"]' in css
    assert '[data-family="knowledge"]' in css
    assert '[data-family="capability"]' in css
    assert 'prefers-reduced-motion: reduce' in css
    assert '.v2-indicator-rail' in css
    assert '.v2-card-back' in css

    assert 'ROOT_SPACES = ["pantheon", "decisions", "affaires", "connaissances", "outils"]' in javascript
    assert 'state.navigator.descend' in javascript
    assert 'state.navigator.ascend' in javascript
    assert 'state.navigator.returnToRoot' in javascript
    assert 'state.flipped' in javascript
    assert 'PostgreSQL Agency Data' in javascript
    assert 'la liste Agency Data globale n’est pas encore branchée' not in javascript.lower()


def test_v2_does_not_claim_hermes_handoff_or_global_agency_data_is_live() -> None:
    html = (COCKPIT / "v2.html").read_text(encoding="utf-8")
    javascript = (COCKPIT / "v2_app.js").read_text(encoding="utf-8")

    assert "La liste globale PostgreSQL Agency Data n’est pas encore branchée" in html
    assert "Handoff Hermes non branché" in html
    assert 'disabled title="Handoff Hermes non branché' in html
    assert "la liste Agency Data globale n’est pas encore branchée" in javascript
    assert "direct_database_credentials" not in javascript
    assert "notion_token" not in javascript.lower()
