from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "cockpit" / "COCKPIT_CLEANUP_SEQUENCE.md"


def test_cleanup_sequence_keeps_architectural_boundaries_explicit() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "Stage 1 — retired visual authorities" in text
    assert "Stage 2 — neutral entrypoints" in text
    assert "Stage 3 — neutral renderer contract" in text
    assert "Stage 4 — functional DOM identifiers" in text
    assert "visual projection != semantic model" in text
    assert "UI status != authorization" in text
    assert "Swiper remains isolated" in text
