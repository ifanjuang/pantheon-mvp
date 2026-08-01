from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"


def test_entrypoint_readme_matches_active_files() -> None:
    text = (COCKPIT / "README_ENTRYPOINTS.md").read_text(encoding="utf-8")
    for filename in (
        "cockpit_bootstrap.js",
        "live_bootstrap.js",
        "live_collection_adapter.js",
        "shell_controls.js",
    ):
        assert filename in text
        assert (COCKPIT / filename).exists()
