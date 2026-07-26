from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"


def test_v2_uses_native_renderer_without_presentation_adapter():
    html = (COCKPIT / "v2.html").read_text(encoding="utf-8")

    assert 'src="v2_app_native.js"' in html
    assert 'src="v2_app.js"' not in html
    assert 'src="v2_card_presentation.js"' not in html


def test_native_renderer_exposes_one_contacts_card_per_project():
    renderer = (COCKPIT / "v2_app_native.js").read_text(encoding="utf-8")

    assert 'entity_type: "project_contacts"' in renderer
    assert 'title: "Contacts"' in renderer
    assert 'setChildren(contactsId, [])' in renderer
    assert "normalizeParticipation" not in renderer
    assert "participationContainerId" not in renderer


def test_native_renderer_uses_unified_card_projection_fields():
    renderer = (COCKPIT / "v2_app_native.js").read_text(encoding="utf-8")
    structured = (COCKPIT / "structured_interface.js").read_text(encoding="utf-8")

    for field in (
        "category",
        "index",
        "date",
        "author",
        "type_tags",
        "subject_tags",
        "limits",
        "available_actions",
    ):
        assert field in structured

    assert "model.type_tags" in renderer
    assert "model.subject_tags" in renderer
    assert "model.limits" in renderer


def test_handoff_machine_identity_contract_is_preserved():
    renderer = (COCKPIT / "v2_app_native.js").read_text(encoding="utf-8")
    handoff = (COCKPIT / "v2_handoff.js").read_text(encoding="utf-8")

    assert 'className = "v2-entity-id"' in renderer
    assert 'v2-card-kicker--machine' in renderer
    assert '.v2-entity-id' in handoff
    assert '.v2-card-back .v2-card-kicker' in handoff


def test_native_renderer_keeps_type_subject_status_and_limits_separate():
    renderer = (COCKPIT / "v2_app_native.js").read_text(encoding="utf-8")

    assert "registries.typeTags" in renderer
    assert "registries.subjectTags" in renderer
    assert "registries.statuses" in renderer
    assert "registries.limits" in renderer
    assert 'className = "v2-card-type-tags"' in renderer
    assert 'className = "v2-card-states"' in renderer
    assert 'className = "v2-back-tag-labels"' in renderer
