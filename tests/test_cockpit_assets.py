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
    ROOT / "mvp_vertical" / "cockpit" / "information_architecture.js",
    ROOT / "mvp_vertical" / "cockpit" / "capability_reconciliation.js",
    ROOT / "mvp_vertical" / "cockpit" / "demo.js",
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


def test_live_cockpit_exposes_five_primary_spaces_and_ia_layer() -> None:
    html = (ROOT / "mvp_vertical" / "cockpit" / "index.html").read_text(encoding="utf-8")
    javascript = (
        ROOT / "mvp_vertical" / "cockpit" / "information_architecture.js"
    ).read_text(encoding="utf-8")
    reconciliation = (
        ROOT / "mvp_vertical" / "cockpit" / "capability_reconciliation.js"
    ).read_text(encoding="utf-8")
    css = (
        ROOT / "mvp_vertical" / "cockpit" / "styles" / "information_architecture.css"
    ).read_text(encoding="utf-8")

    for space in ("Pantheon", "Affaires", "Connaissances", "Outils", "Décisions"):
        assert f">{space}</button>" in html
    assert 'src="information_architecture.js"' in html
    assert 'src="capability_reconciliation.js"' in html
    assert html.index('src="knowledge_updates.js"') < html.index('src="information_architecture.js"')
    assert html.index('src="information_architecture.js"') < html.index('src="capability_reconciliation.js"')

    assert '["pantheon", "Pantheon"]' in javascript
    assert '["affaires", "Affaires"]' in javascript
    assert '["connaissances", "Connaissances"]' in javascript
    assert '["outils", "Outils"]' in javascript
    assert '["decisions", "Décisions"]' in javascript
    assert 'frame: "project"' in javascript
    assert 'frame: "knowledge-folder"' in javascript
    assert 'frame: "directory"' in javascript
    assert 'frame: "decision"' in javascript
    assert 'frame: "tool"' in javascript
    assert 'Decision Request / Gate · pas encore une Decision' in javascript
    assert 'installed ≠ approved' in javascript
    assert "HermesCapabilityExecutor" in reconciliation
    assert "Candidats empilés · adoption non établie" in reconciliation
    assert 'data-frame="project"' in css
    assert 'data-frame="knowledge-folder"' in css


def test_static_demo_reuses_cockpit_assets_and_blocks_network() -> None:
    html = (ROOT / "mvp_vertical" / "cockpit" / "demo.html").read_text(
        encoding="utf-8"
    )
    javascript = (ROOT / "mvp_vertical" / "cockpit" / "demo.js").read_text(
        encoding="utf-8"
    )
    html_lower = html.lower()

    assert 'href="styles/index.css"' in html
    for script in (
        "app.js",
        "resources.js",
        "effects.js",
        "knowledge_updates.js",
        "demo.js",
    ):
        assert f'src="{script}"' in html

    assert "window.PANTHEON_COCKPIT_DEMO = true" in html
    assert "window.fetch = async" in html
    assert "accès réseau désactivé" in html_lower
    assert "données fictives" in html_lower

    # The hierarchical demo owns synthetic projects and a separate global
    # Reference Space, then projects the selected project into the shared
    # cockpit state. The test checks the current data contract rather than the
    # retired flat top-level fixture assignments.
    assert "const references = [" in javascript
    assert "const projects = [" in javascript
    assert "workIssues: [" in javascript
    assert "documents: [" in javascript
    assert "referenceIds:" in javascript
    assert "state.documents = project.documents" in javascript
    assert "state.workIssues = project.workIssues" in javascript
    assert "state.knowledge = references.filter" in javascript
    assert "state.resourceProfiles = {" in javascript
    assert "fetch(" not in javascript


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


def test_mobile_editor_recovers_legacy_offline_revisions_before_queue_cleanup() -> None:
    javascript = (ROOT / "mvp_vertical" / "mobile_editor" / "app.js").read_text(
        encoding="utf-8"
    )

    assert "function legacyDraftKey" in javascript
    assert "function migrateLegacyRevisions" in javascript
    assert "operation?.type !== \"revision\"" in javascript
    assert "localStorage.setItem(" in javascript
    assert "legacyDraftKey(knowledgeId)" in javascript
    assert "recovered?.markdown ?? remoteMarkdown" in javascript
    assert "localStorage.removeItem(legacyDraftKey(updated.knowledge_id))" in javascript
    assert "ancienne(s) révision(s) récupérée(s) comme brouillon local" in javascript
    assert "retiredRevisions" not in javascript


def test_cockpit_update_retries_reuse_idempotency_and_refresh_all_projections() -> None:
    javascript = (
        ROOT / "mvp_vertical" / "cockpit" / "knowledge_updates.js"
    ).read_text(encoding="utf-8")

    assert "const updateIdempotencyKey = idempotencyKey();" in javascript
    assert "idempotency_key: updateIdempotencyKey" in javascript
    assert 'document.addEventListener("pantheon:knowledge-updated"' in javascript
    assert "load.click()" in javascript


def test_removed_site_list_registry_is_not_advertised_as_runtime_configuration() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "MVP_SITE_LISTS_JSON" not in compose
    assert "/config" not in compose
    assert not (ROOT / "config" / "site_lists.json").exists()
    assert not (ROOT / "config" / "README.md").exists()
