"""Static and boundary checks for the read-only Cockpit knowledge-map lens."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = ROOT / "mvp_vertical" / "cockpit" / "map"
SCRIPTS = [
    MAP_DIR / "map_graph_model.js",
    MAP_DIR / "map_layouts.js",
    MAP_DIR / "map_view.js",
]


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


def test_map_lens_is_read_only() -> None:
    """The lens must reshape/draw only: no network, no runtime side effects."""
    forbidden = ("fetch(", "XMLHttpRequest", "WebSocket", "localStorage", "sessionStorage")
    for script in SCRIPTS:
        source = script.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source, f"{script.name} must stay read-only (found {token!r})"


def test_map_declares_boundary_invariants() -> None:
    readme = (MAP_DIR / "README.md").read_text(encoding="utf-8")
    for invariant in ("map view != data model", "projection != authority", "read-only"):
        assert invariant in readme, f"README must declare invariant: {invariant!r}"


def test_map_graph_model_exposes_pure_build() -> None:
    source = (MAP_DIR / "map_graph_model.js").read_text(encoding="utf-8")
    assert "window.PantheonMapGraphModel" in source
    assert "function build(" in source
