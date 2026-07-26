from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "mvp_vertical" / "vendor" / "pantheon"


def test_project_claim_schema_is_vendored_and_pinned() -> None:
    schema = yaml.safe_load((VENDOR / "project_claim.schema.yaml").read_text(encoding="utf-8"))
    assert schema["title"] == "Pantheon Next Project Claim"
    assert schema["x-boundary"]["system_of_record_mutation"] is False
    assert "backing_ref" in schema["properties"]

    pinned = (VENDOR / "UPSTREAM_COMMIT").read_text(encoding="utf-8").strip()
    assert pinned == "375fc115d2e946b82dbd27eb430d31c84a95236d"


def test_revendor_includes_project_claim_schema() -> None:
    script = (ROOT / "tools" / "revendor.sh").read_text(encoding="utf-8")
    assert '"project_claim.schema.yaml"' in script
