"""Static asset checks for the cards-first cockpit candidate."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    ROOT / "mvp_vertical" / "cockpit" / "app.js",
    ROOT / "mvp_vertical" / "cockpit" / "resources.js",
    ROOT / "mvp_vertical" / "cockpit" / "effects.js",
    ROOT / "mvp_vertical" / "cockpit" / "knowledge_updates.js",
    ROOT / "mvp_vertical" / "mobile_editor" / "app.js",
    ROOT / "mvp_vertical" / "mobile_editor" / "sw.js",
]


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: str(path.relative_to(ROOT)))
def test_cockpit_javascript_parses(script: Path) -> None:
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


def test_mobile_editor_exposes_and_clears_device_local_data() -> None:
    html = (ROOT / "mvp_vertical" / "mobile_editor" / "index.html").read_text(
        encoding="utf-8"
    )
    javascript = (ROOT / "mvp_vertical" / "mobile_editor" / "app.js").read_text(
        encoding="utf-8"
    )

    assert 'id="clear-local"' in html
    assert "sans chiffrement applicatif" in html
    assert '"pantheon-knowledge:"' in javascript
    assert '"pantheon-project:"' in javascript
    assert "localStorage.removeItem" in javascript
    assert 'sessionStorage.removeItem("pantheon-human-actor")' in javascript
    assert '$("clear-local").onclick = clearLocalData' in javascript
