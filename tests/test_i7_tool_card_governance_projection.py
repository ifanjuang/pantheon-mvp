from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"
CATALOG = COCKPIT / "tool_catalog.json"
BOOTSTRAP = COCKPIT / "live_bootstrap.js"
PROJECTION = COCKPIT / "projection" / "tool_governance_projection.js"


def test_tool_catalog_remains_explicitly_non_authoritative() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert catalog["authority"]["catalogue_is_authority"] is False
    assert catalog["authority"]["approval_owned_by"] == "human"
    assert "runtime" in catalog["authority"]["runtime_owned_by"].lower()


def test_tool_governance_projection_is_loaded_after_structured_interface() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    structured = source.index('"structured_interface.js"')
    governance = source.index('"projection/tool_governance_projection.js"')
    cockpit = source.index('"projection/cockpit_projection.js"')
    assert structured < governance < cockpit


def test_tool_governance_projection_keeps_exact_release_axes_separate() -> None:
    source = PROJECTION.read_text(encoding="utf-8")
    for token in (
        "binding_id",
        "implementation_anchor",
        "activation_state",
        "activation_scope",
        "compatibility_status",
        "safety_status",
        "freshness_status",
        "source_observation_ref",
    ):
        assert token in source

    assert '"Effet d’autorisation", "Aucun — projection uniquement"' in source
    assert "task_authorized" not in source
    assert "evidence_effect" not in source


def test_missing_governance_data_is_not_promoted_to_positive_state() -> None:
    source = PROJECTION.read_text(encoding="utf-8")
    assert 'fallback = "Non observé"' in source
    assert '"Non activé / non observé"' in source
    assert '"Non observée"' in source
    assert '"compatible"' not in source
    assert '"qualified"' not in source
    assert '"approved"' not in source
