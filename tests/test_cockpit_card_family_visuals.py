from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"


def test_card_family_styles_load_between_shared_cards_and_geometry() -> None:
    html = (COCKPIT / "index.html").read_text(encoding="utf-8")

    shared = 'href="styles/v3_living_cards.css"'
    tokens = 'href="styles/v3_card_tokens.css"'
    project = 'href="styles/v3_card_project.css"'
    work = 'href="styles/v3_card_work.css"'
    geometry = 'href="styles/v3_geometry.css"'

    for reference in (shared, tokens, project, work, geometry):
        assert reference in html

    assert html.index(shared) < html.index(tokens)
    assert html.index(tokens) < html.index(project) < html.index(geometry)
    assert html.index(tokens) < html.index(work) < html.index(geometry)


def test_project_and_work_visuals_are_isolated_by_family() -> None:
    project = (COCKPIT / "styles" / "v3_card_project.css").read_text(encoding="utf-8")
    work = (COCKPIT / "styles" / "v3_card_work.css").read_text(encoding="utf-8")

    assert '[data-family="project"]' in project
    assert '[data-family="work"]' not in project
    assert '[data-family="work"]' in work
    assert '[data-family="project"]' not in work

    for css in (project, work):
        assert 'data-family="information"' not in css
        assert 'data-family="tool"' not in css
        assert 'data-family="decision"' not in css


def test_shared_project_marker_is_twelve_pixels_and_has_no_material_effects() -> None:
    tokens = (COCKPIT / "styles" / "v3_card_tokens.css").read_text(encoding="utf-8")
    project = (COCKPIT / "styles" / "v3_card_project.css").read_text(encoding="utf-8")
    work = (COCKPIT / "styles" / "v3_card_work.css").read_text(encoding="utf-8")

    assert "--v3-card-accent-size: 12px" in tokens
    assert "var(--v3-card-accent-size)" in work
    assert "box-shadow: none" in project
    assert "box-shadow: none" in work

    retired_material_terms = ("v3-project-paper", "background-size: auto, 100% 2.4rem", "inset 0 1px")
    for term in retired_material_terms:
        assert term not in project


def test_family_visuals_do_not_change_card_dom_or_business_model() -> None:
    renderer = (COCKPIT / "v3" / "collection" / "card_renderer.js").read_text(encoding="utf-8")
    provider = (COCKPIT / "v3" / "providers" / "demo_provider.js").read_text(encoding="utf-8")

    assert "article.dataset.family = item.family" in renderer
    assert '"project"' in provider
    assert '"work"' in provider

    for visual_file in ("v3_card_tokens", "v3_card_project", "v3_card_work"):
        assert visual_file not in renderer
        assert visual_file not in provider


def test_visual_language_document_keeps_presentation_boundary_explicit() -> None:
    document = (ROOT / "docs" / "cockpit" / "CARD_VISUAL_LANGUAGE.md").read_text(encoding="utf-8")

    assert "visual projection != semantic model" in document
    assert "project colour != status" in document
    assert "UI status != authorization" in document
    assert "Work" in document and "12 × 12 px" in document
    assert "Folder" in document and "12 px high" in document
    assert "organic outline blobs, not circles or rings" in document
