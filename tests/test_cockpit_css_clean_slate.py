from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"
STYLES = COCKPIT / "styles"


def test_clean_slate_has_four_authority_files() -> None:
    expected = {"cockpit.css", "cards.css", "families.css", "editors.css"}
    for name in expected:
        assert (STYLES / name).is_file()


def test_css_layers_and_responsibilities_are_explicit() -> None:
    cockpit = (STYLES / "cockpit.css").read_text(encoding="utf-8")
    cards = (STYLES / "cards.css").read_text(encoding="utf-8")
    families = (STYLES / "families.css").read_text(encoding="utf-8")
    editors = (STYLES / "editors.css").read_text(encoding="utf-8")

    layer_order = "@layer reset, tokens, shell, navigation, cards, families, states, editors, responsive;"
    for css in (cockpit, cards, families, editors):
        assert layer_order in css

    assert ".v2-card-inner" in cards
    assert ".v3-card-blob" in cards
    assert '[data-kind="work"]' in cards
    assert '[data-kind="folder"]' in cards
    assert '[data-family="knowledge"]' in families
    assert '[data-family="skills"]' in families
    assert "display:" not in families
    assert "position:" not in families


def test_renderer_projects_visual_axes_without_css_filename_coupling() -> None:
    renderer = (COCKPIT / "v3" / "collection" / "card_renderer.js").read_text(encoding="utf-8")

    assert "article.dataset.level = visualLevel(item)" in renderer
    assert "article.dataset.kind = visualKind(item)" in renderer
    assert 'return "folder"' in renderer
    assert 'return "work"' in renderer

    for filename in ("cockpit.css", "cards.css", "families.css", "editors.css"):
        assert filename not in renderer


def test_visual_markers_remain_twelve_pixels_and_flat() -> None:
    cockpit = (STYLES / "cockpit.css").read_text(encoding="utf-8")
    cards = (STYLES / "cards.css").read_text(encoding="utf-8")

    assert "--cockpit-accent-size: 12px" in cockpit
    assert "var(--cockpit-accent-size)" in cards
    for forbidden in ("box-shadow", "filter: blur", "backdrop-filter"):
        assert forbidden not in cards
