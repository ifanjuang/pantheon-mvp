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

    assert ".card-inner" in cards
    assert ".card-blob" in cards
    assert ".card-front::before" in cards
    assert '[data-kind="work"]' not in cards
    assert '[data-kind="folder"]' not in cards
    assert '[data-family="knowledge"]' in families
    assert '[data-family="skills"]' in families
    assert "display:" not in families
    assert "position:" not in families


def test_renderer_projects_visual_axes_without_style_presets() -> None:
    renderer = (COCKPIT / "v3" / "collection" / "card_renderer.js").read_text(encoding="utf-8")

    assert "article.dataset.level = visualLevel(item)" in renderer
    assert "article.dataset.kind = visualKind(item)" in renderer
    assert "article.dataset.family" in renderer
    assert "article.dataset.status" in renderer
    assert 'return "folder"' in renderer
    assert 'return "work"' in renderer
    assert "BLOB_FAMILIES" not in renderer
    assert "blobSignature" not in renderer
    assert 'article.className = "card"' in renderer

    for filename in ("cockpit.css", "cards.css", "families.css", "editors.css"):
        assert filename not in renderer


def test_visual_markers_remain_twelve_pixels_and_flat() -> None:
    cockpit = (STYLES / "cockpit.css").read_text(encoding="utf-8")
    cards = (STYLES / "cards.css").read_text(encoding="utf-8")
    families = (STYLES / "families.css").read_text(encoding="utf-8")

    assert "--cockpit-accent-size: 12px" in cockpit
    assert "var(--cockpit-accent-size)" in families
    assert "--marker-clip" in cards
    for forbidden in ("box-shadow", "filter: blur", "backdrop-filter"):
        assert forbidden not in cards
        assert forbidden not in families


def test_level_family_kind_status_and_context_stay_independent() -> None:
    families = (STYLES / "families.css").read_text(encoding="utf-8")

    for level in ("pack", "booster", "card"):
        assert f'[data-level="{level}"]' in families

    for family in ("pantheon", "affaires", "knowledge", "skills"):
        assert f'[data-family="{family}"]' in families

    for kind in ("project", "work", "folder"):
        assert f'[data-kind="{kind}"]' in families

    assert "--project-accent" in families
    assert "data-status" not in families
