from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"


def test_entrypoint_contract_lists_existing_files_only() -> None:
    names = (COCKPIT / ".entrypoint-contract").read_text(encoding="utf-8").splitlines()
    assert names == [
        "cockpit_bootstrap.js",
        "live_bootstrap.js",
        "live_collection_adapter.js",
        "shell_controls.js",
    ]
    assert all((COCKPIT / name).is_file() for name in names)
