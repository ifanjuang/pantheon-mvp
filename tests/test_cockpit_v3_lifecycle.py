"""Architecture budgets for the cockpit navigation core.

These are static guards, not runtime measurements: they pin the contracts so a
later edit cannot quietly reintroduce a Swiper-shaped cockpit or mount a whole
collection into the DOM again.

Contracts:
  - Swiper exists in exactly one module (the MotionAdapter);
  - the cockpit never calls Swiper's slide APIs directly;
  - at most three projections are mounted (active plus one neighbour each side);
  - an already-resident array is applied at once, never faked as a stream.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"
ADAPTER = "v3/collection/motion_adapter.js"

# Every cockpit module that must stay free of Swiper.
SWIPER_FREE = (
    "v3/collection/navigation_state.js",
    "v3/collection/collection_provider.js",
    "v3/collection/collection_controller.js",
    "v3/collection/level_controller.js",
    "v3/collection/card_renderer.js",
    "v3/demo_collection_app.js",
)


def _read(rel: str) -> str:
    return (COCKPIT / rel).read_text(encoding="utf-8")


def test_swiper_is_confined_to_the_motion_adapter() -> None:
    adapter = _read(ADAPTER)
    assert "new window.Swiper" in adapter

    for rel in SWIPER_FREE:
        source = _read(rel)
        assert "new window.Swiper" not in source, rel
        assert "new Swiper(" not in source, rel


def test_cockpit_never_drives_swiper_slide_apis_directly() -> None:
    # These belong to the adapter alone, so the engine stays replaceable.
    for rel in SWIPER_FREE + ("v3_swiper.js",):
        source = _read(rel)
        for forbidden in ("appendSlide", "removeAllSlides", "updateSlides", "slideTo(", "slidePrev(", "slideNext("):
            assert forbidden not in source, f"{rel} calls {forbidden}"


def test_at_most_three_projections_are_mounted() -> None:
    adapter = _read(ADAPTER)

    # Swiper Virtual keeps only the active slide plus one neighbour per side.
    assert "virtual" in adapter
    assert "addSlidesBefore: 1" in adapter
    assert "addSlidesAfter: 1" in adapter


def test_resident_arrays_are_not_fake_streamed() -> None:
    provider = _read("v3/collection/collection_provider.js")

    assert "isAsyncIterable" in provider
    assert "Symbol.asyncIterator" in provider
    # An array must be applied in one go, with no per-frame drip.
    assert "requestAnimationFrame" not in provider


def test_demo_html_targets_the_single_cockpit_page() -> None:
    demo_html = _read("demo.html")
    assert "index.html?mode=demo" in demo_html
    assert "v2.html?mode=demo" not in demo_html
