"""Static and boundary checks for the read-only Cockpit knowledge-map lens."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = ROOT / "mvp_vertical" / "cockpit" / "map"
SCRIPTS = sorted(MAP_DIR.glob("*.js"))
FORBIDDEN = ("fetch(", "XMLHttpRequest", "WebSocket", "localStorage", "sessionStorage")


def test_map_scripts_present() -> None:
    names = {p.name for p in SCRIPTS}
    assert {
        "map_graph_model.js", "map_layouts.js", "map_view.js",
        "map_tokens.js", "map_corroboration.js", "map_bundle.js", "map_mount.js",
    } <= names


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.name)
def test_map_javascript_parses(script: Path) -> None:
    node = shutil.which("node")
    if node is None:  # pragma: no cover - depends on the runner image
        pytest.skip("Node.js is unavailable; JavaScript syntax check skipped")
    result = subprocess.run(
        [node, "--check", str(script)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.name)
def test_map_lens_is_read_only(script: Path) -> None:
    """The lens must reshape/draw only: no network, no persisted side effects."""
    source = script.read_text(encoding="utf-8")
    for token in FORBIDDEN:
        assert token not in source, f"{script.name} must stay read-only (found {token!r})"


def test_map_declares_boundary_invariants() -> None:
    readme = (MAP_DIR / "README.md").read_text(encoding="utf-8")
    for invariant in ("map view != data model", "projection != authority", "read-only"):
        assert invariant in readme, f"README must declare invariant: {invariant!r}"


def test_map_modules_expose_globals() -> None:
    expected = {
        "map_graph_model.js": "window.PantheonMapGraphModel",
        "map_layouts.js": "window.PantheonMapLayouts",
        "map_view.js": "window.PantheonMapView",
        "map_tokens.js": "window.PantheonMapTokens",
        "map_corroboration.js": "window.PantheonMapCorroboration",
        "map_bundle.js": "window.PantheonMapBundle",
        "map_mount.js": "window.PantheonMapMount",
    }
    for name, symbol in expected.items():
        source = (MAP_DIR / name).read_text(encoding="utf-8")
        assert symbol in source, f"{name} must expose {symbol}"


def test_projection_graph_exposure_is_read_only_hook() -> None:
    """The live hook must expose a frozen snapshot and only dispatch an event."""
    source = (ROOT / "mvp_vertical" / "cockpit" / "projection" / "cockpit_projection.js").read_text(encoding="utf-8")
    assert "window.PantheonCockpitGraph = Object.freeze(" in source
    assert "pantheon:graph-updated" in source
