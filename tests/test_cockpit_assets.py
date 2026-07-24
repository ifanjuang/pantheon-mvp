"""Static and bounded-behavior checks for the cards-first cockpit candidate."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    ROOT / "mvp_vertical" / "cockpit" / "structured_interface.js",
    ROOT / "mvp_vertical" / "cockpit" / "context_resolver.js",
    ROOT / "mvp_vertical" / "cockpit" / "notion_agency_binding.js",
    ROOT / "mvp_vertical" / "cockpit" / "app.js",
    ROOT / "mvp_vertical" / "cockpit" / "resources.js",
    ROOT / "mvp_vertical" / "cockpit" / "effects.js",
    ROOT / "mvp_vertical" / "cockpit" / "knowledge_updates.js",
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


def test_cockpit_v2_foundations_are_loaded_before_legacy_renderers() -> None:
    html = (ROOT / "mvp_vertical" / "cockpit" / "index.html").read_text(encoding="utf-8")
    resolver = (ROOT / "mvp_vertical" / "cockpit" / "context_resolver.js").read_text(encoding="utf-8")
    notion = (ROOT / "mvp_vertical" / "cockpit" / "notion_agency_binding.js").read_text(encoding="utf-8")
    contract = (ROOT / "mvp_vertical" / "cockpit" / "structured_interface.js").read_text(encoding="utf-8")

    assert 'src="structured_interface.js"' in html
    assert 'src="context_resolver.js"' in html
    assert 'src="notion_agency_binding.js"' in html
    assert html.index('src="structured_interface.js"') < html.index('src="context_resolver.js"')
    assert html.index('src="context_resolver.js"') < html.index('src="notion_agency_binding.js"')
    assert html.index('src="notion_agency_binding.js"') < html.index('src="app.js"')

    for prefix in ('_', '"#"', '"@"', '"*"'):
        assert prefix in resolver
    assert "registerProvider" in resolver
    assert "Promise.allSettled" in resolver
    assert "namespace_required" in resolver
    assert "searchableText" in resolver
    assert "matched_field" in resolver
    assert "selected: false" in resolver

    assert '"disabled", "read_only"' in notion
    assert 'provider: "notion"' in notion
    assert 'effect: "read_only"' in notion
    assert "direct_browser_credentials: false" in notion
    assert "write_effect: false" in notion
    for collection in ("_Affaires", "_Personnes", "_Sociétés", "_Intervenants"):
        assert collection in notion

    assert '"pantheon", "decisions", "affaires", "connaissances", "outils"' in contract
    assert '"conversation", "container", "entity"' in contract
    assert "buildTagProjection" in contract
    assert "buildCardContextEnvelope" in contract
    assert "scope_widened_implicitly: false" in contract


def _run_node(script: str) -> subprocess.CompletedProcess[str]:
    node = shutil.which("node")
    if node is None:  # pragma: no cover - depends on the runner image
        pytest.skip("Node.js is unavailable; JavaScript behavior check skipped")
    return subprocess.run(
        [node, "-e", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_context_resolver_composes_providers_and_explains_matches() -> None:
    script = r'''
      global.window = {};
      require("./mvp_vertical/cockpit/context_resolver.js");
      const resolver = window.PantheonContextResolver;

      (async () => {
        const detachA = resolver.registerProvider("affaires", async () => [
          { id: "p-lieurey", entity_type: "project", label: "Lieurey", tags: ["ABF"] },
        ]);
        const detachB = resolver.registerProvider("affaires", async () => [
          { id: "p-lieuvin", entity_type: "project", label: "Lieuvin", tags: ["Neuf"] },
        ]);

        const projects = await resolver.resolve("_LIE");
        if (projects.results.length !== 2) throw new Error("providers were not composed");
        if (projects.results[0].matched_field !== "label") throw new Error("prefix match not explained");
        if (projects.results.some(item => item.selected !== false)) throw new Error("search result leaked selection state");

        const tagged = await resolver.resolve("*abf");
        if (tagged.results.length !== 1 || tagged.results[0].entity_id !== "p-lieurey") {
          throw new Error("global tag search failed");
        }
        if (tagged.results[0].matched_field !== "tag") throw new Error("tag match reason missing");

        detachA();
        detachB();
      })().catch(error => { console.error(error); process.exit(1); });
    '''
    result = _run_node(script)
    assert result.returncode == 0, result.stderr


def test_optional_notion_binding_registers_read_only_agency_projections() -> None:
    script = r'''
      global.window = {};
      require("./mvp_vertical/cockpit/context_resolver.js");
      require("./mvp_vertical/cockpit/notion_agency_binding.js");

      const resolver = window.PantheonContextResolver;
      const collections = window.PantheonNotionAgencyBinding.defaultCollections;
      const transport = async request => {
        if (request.effect !== "read_only") throw new Error("write effect requested");
        if (request.collection === collections.affaires) return [{
          id: "notion-project-lieurey",
          url: "https://notion.example/lieurey",
          fields: { Code: "Lieurey", Statut: "En cours", Phase: "PRO", Lieu: "Lieurey", "Zone PLU": "U" },
        }];
        if (request.collection === collections.people) return [{
          id: "notion-person-helene",
          fields: { Nom: "Hélène Leroux", "E-mail": "helene@example.test" },
        }];
        if (request.collection === collections.organizations) return [{
          id: "notion-company",
          fields: { Name: "BET Exemple", siret: "12345678900000" },
        }];
        if (request.collection === collections.participations) return [{
          id: "notion-participation",
          fields: { Code: "BET-STRUCT", "Rôle": "BET STRUCTURE", Type: "Maîtrise d'Oeuvre" },
        }];
        return [];
      };

      (async () => {
        const binding = window.PantheonNotionAgencyBinding.create({
          mode: "read_only",
          workspaceLabel: "IFJA",
          transport,
          resolver,
        });
        binding.attach();

        const project = await resolver.resolve("_LIE");
        if (project.results[0]?.entity_type !== "project") throw new Error("Notion project projection missing");
        if (project.results[0]?.source?.system !== "notion") throw new Error("Notion source attribution missing");

        const person = await resolver.resolve("@helene");
        if (person.results[0]?.entity_type !== "person") throw new Error("Notion people projection missing");

        const organization = await resolver.resolve("*123456789");
        if (organization.results[0]?.entity_type !== "organization") throw new Error("Notion global projection missing");

        const status = binding.status();
        if (status.write_effect !== false || status.direct_browser_credentials !== false) {
          throw new Error("Notion binding boundary regressed");
        }

        binding.detach();
      })().catch(error => { console.error(error); process.exit(1); });
    '''
    result = _run_node(script)
    assert result.returncode == 0, result.stderr


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
