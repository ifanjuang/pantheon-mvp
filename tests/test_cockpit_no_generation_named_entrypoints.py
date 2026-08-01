from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"


def test_canonical_entrypoint_chain_has_no_generation_named_files() -> None:
    html = (COCKPIT / "index.html").read_text(encoding="utf-8")
    bootstrap = (COCKPIT / "cockpit_bootstrap.js").read_text(encoding="utf-8")
    live = (COCKPIT / "live_bootstrap.js").read_text(encoding="utf-8")
    chain = "\n".join((html, bootstrap, live))
    for retired in ("v2_bootstrap.js", "v3_bootstrap.js", "v2_shell_controls.js", "v3_swiper.js"):
        assert retired not in chain
