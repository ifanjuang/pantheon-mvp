"""Static asset checks for the cards-first cockpit candidate."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "mvp_vertical" / "cockpit" / "app.js"


def test_cockpit_javascript_parses() -> None:
    node = shutil.which("node")
    if node is None:  # pragma: no cover - depends on the runner image
        pytest.skip("Node.js is unavailable; JavaScript syntax check skipped")

    result = subprocess.run(
        [node, "--check", str(APP_JS)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
