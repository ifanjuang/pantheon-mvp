"""Static boundary checks for the Cockpit V2 Hermes handoff preview dock."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"


def test_v2_handoff_javascript_parses() -> None:
    node = shutil.which("node")
    if node is None:  # pragma: no cover
        pytest.skip("Node.js is unavailable; JavaScript syntax check skipped")
    result = subprocess.run(
        [node, "--check", str(COCKPIT / "v2_handoff.js")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_v2_handoff_prepares_but_cannot_execute() -> None:
    html = (COCKPIT / "v2.html").read_text(encoding="utf-8")
    javascript = (COCKPIT / "v2_handoff.js").read_text(encoding="utf-8")
    css = (COCKPIT / "styles" / "v2_handoff.css").read_text(encoding="utf-8")

    assert 'id="v2-handoff-question"' in html
    assert 'id="v2-handoff-prepare"' in html
    assert 'id="v2-handoff-execute" type="button" disabled' in html
    assert 'src="v2_handoff.js"' in html
    assert 'href="styles/v2_handoff.css"' in html

    assert '../v1/cockpit/hermes-handoffs/preview' in javascript
    assert 'scope_widened_implicitly: false' in javascript
    assert 'descendants: []' in javascript
    assert 'source_refs: []' in javascript
    assert 'selected_context: selectedContext.map' in javascript
    assert 'execution non autorisée' in javascript
    assert 'aucun Work Issue créé' in javascript
    assert 'pantheon:v2-context-changed' in javascript

    assert '.v2-handoff-preview' in css
    assert '.v2-handoff-question' in css
