"""Static guards for the Cockpit V3 Swiper lifecycle (issue #108).

These checks are text-level, not runtime: they pin the architectural contract so
a future edit cannot silently reintroduce the destroy/rebuild pattern the refactor
removed.

Contract:
  - Swiper is instantiated only inside the shared controllers, never in the demo
    wiring or the live adapter.
  - The CollectionController bootstraps with a `New` slide plus a placeholder and
    then only appends further slides.
  - Neither the demo app nor the live adapter destroys/recreates Swiper between
    collections; switching collections reuses the instance.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"


def _read(rel: str) -> str:
    return (COCKPIT / rel).read_text(encoding="utf-8")


def test_swiper_is_only_constructed_inside_controllers() -> None:
    # Business wiring must not own Swiper construction.
    for rel in ("v3/demo_collection_app.js", "v3_swiper.js"):
        source = _read(rel)
        assert "new window.Swiper" not in source, rel
        assert "new Swiper(" not in source, rel

    # The controllers are the only place Swiper is created.
    controller = _read("v3/collection/collection_controller.js")
    level = _read("v3/collection/level_controller.js")
    assert "new window.Swiper" in controller
    assert "new window.Swiper" in level


def test_collection_controller_uses_placeholder_then_append() -> None:
    controller = _read("v3/collection/collection_controller.js")
    # Bootstrap adds the New slide and a placeholder, first item replaces the
    # placeholder, the rest are appended.
    assert "renderPlaceholder()" in controller
    assert "appendSlide" in controller
    # No full rebuild: the instance is reused via removeAllSlides, not destroy.
    assert "removeAllSlides" in controller


def test_old_rebuild_pattern_is_gone() -> None:
    demo = _read("v3/demo_collection_app.js")
    # The per-navigation rebuild helpers must no longer exist.
    assert "destroyLevelDeck" not in demo
    assert "buildHorizontalShell" not in demo
    assert "renderLevelDeck" not in demo
    # The demo now delegates the Swiper lifecycle to the shared controllers.
    assert "createLevelController" in demo

    adapter = _read("v3_swiper.js")
    # The live adapter no longer monkeypatches the stage; it drives a controller.
    assert "stage.replaceChildren =" not in adapter
    assert "createCollectionController" in adapter


def test_demo_html_targets_cockpit_v3() -> None:
    demo_html = _read("demo.html")
    assert "v3.html?mode=demo" in demo_html
    assert "v2.html?mode=demo" not in demo_html
