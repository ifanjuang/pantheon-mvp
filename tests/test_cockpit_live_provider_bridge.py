"""Regression guard for the live renderer -> LiveProvider -> CockpitSnapshot bridge."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COCKPIT = ROOT / "mvp_vertical" / "cockpit"


def test_live_adapter_keeps_projected_siblings_inside_snapshot_envelope() -> None:
    adapter = (COCKPIT / "live_collection_adapter.js").read_text(encoding="utf-8")

    # LiveProvider owns one explicit object contract. Passing the models array as
    # the first positional argument silently defaults `siblings` to [], which is
    # rendered as "Aucune carte dans cette collection.".
    assert "provider.toSnapshot(projectSnapshotInput(models), activeIndex)" not in adapter
    assert "provider.toSnapshot({" in adapter
    assert "siblings: projectSnapshotInput(models)" in adapter
    assert "index: activeIndex" in adapter

    # CockpitSnapshot stores collection identity under `collection.id`.
    assert "snapshot.collection_id" not in adapter
    assert "snapshot.collection?.id" in adapter
