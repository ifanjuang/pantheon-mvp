from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"


def test_canonical_page_uses_neutral_bootstrap_entrypoint() -> None:
    html = (COCKPIT / "index.html").read_text(encoding="utf-8")
    assert 'src="cockpit_bootstrap.js"' in html
    assert 'src="v3_bootstrap.js"' not in html


def test_neutral_entrypoints_exist_and_historical_names_are_removed() -> None:
    expected = (
        "cockpit_bootstrap.js",
        "live_bootstrap.js",
        "live_collection_adapter.js",
        "shell_controls.js",
    )
    retired = (
        "v3_bootstrap.js",
        "v2_bootstrap.js",
        "v3_swiper.js",
        "v2_shell_controls.js",
    )
    for filename in expected:
        assert (COCKPIT / filename).exists(), filename
    for filename in retired:
        assert not (COCKPIT / filename).exists(), filename


def test_bootstrap_chain_references_only_neutral_entrypoint_names() -> None:
    cockpit = (COCKPIT / "cockpit_bootstrap.js").read_text(encoding="utf-8")
    live = (COCKPIT / "live_bootstrap.js").read_text(encoding="utf-8")

    assert './shell_controls.js' in cockpit
    assert './live_bootstrap.js' in cockpit
    assert './live_collection_adapter.js' in live
    for retired in ("v3_bootstrap.js", "v2_bootstrap.js", "v3_swiper.js", "v2_shell_controls.js"):
        assert retired not in cockpit
        assert retired not in live
