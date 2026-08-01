from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "cockpit" / "ENTRYPOINT_CONTRACT.md"


def test_entrypoint_contract_document_names_active_chain() -> None:
    text = DOC.read_text(encoding="utf-8")
    for name in ("cockpit_bootstrap.js", "live_bootstrap.js", "live_collection_adapter.js", "shell_controls.js"):
        assert name in text
    assert "Functional `v2-*` DOM identifiers" in text
