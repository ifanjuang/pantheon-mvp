from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "document_runtime_synthetic_check.py"


def _load():
    spec = importlib.util.spec_from_file_location("document_runtime_synthetic_check", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _observations(*, hermes="installed_observed"):
    return {
        "observations": [
            {
                "source": "paperless_gateway",
                "paperless_reachability_status": "reachable",
            },
            {"source": "pantheon_pdp", "readiness_status": "ready_observed"},
            {"source": "docling_serve", "reachability_status": "reachable"},
            {"source": "hermes_native_inventory", "installation_status": hermes},
        ]
    }


def test_assessment_requires_all_four_independent_observations():
    module = _load()
    ready = module.assess_observations(_observations())
    assert ready["candidate_ready_for_synthetic_intake"] is True
    assert ready["production_authorization"] is False
    assert ready["safety_status"] == "not_inferred"

    missing_hermes = module.assess_observations(_observations(hermes="not_observed"))
    assert missing_hermes["candidate_ready_for_synthetic_intake"] is False
    assert missing_hermes["checks"]["hermes_skill_installed"] is False


def test_synthetic_contract_guard_requires_marker_and_exact_source(tmp_path):
    module = _load()
    contract = tmp_path / "task-contract.yaml"
    contract.write_text(
        "contract_id: tc.synthetic-check\n"
        "parent_project_id: synthetic-document-runtime\n"
        "source_ref: paperless/42/versions/7/synthetic.pdf\n",
        encoding="utf-8",
    )
    text = module._assert_synthetic_contract(
        contract, "paperless/42/versions/7/synthetic.pdf"
    )
    assert "synthetic-document-runtime" in text

    with pytest.raises(module.CheckError, match="source_ref"):
        module._assert_synthetic_contract(contract, "paperless/42/versions/8/other.pdf")

    real_contract = tmp_path / "real.yaml"
    real_contract.write_text(
        "contract_id: tc.project-client\nsource_ref: paperless/42/versions/7/client.pdf\n",
        encoding="utf-8",
    )
    with pytest.raises(module.CheckError, match="explicitly synthetic"):
        module._assert_synthetic_contract(real_contract, "paperless/42/versions/7/client.pdf")


def test_installed_skill_transport_is_invoked_as_fixed_python_script(tmp_path):
    module = _load()
    root = tmp_path / "pantheon-document-intake"
    script = root / "scripts" / "pantheon_document_intake.py"
    script.parent.mkdir(parents=True)
    script.write_text("# fixture\n", encoding="utf-8")
    observed = {}

    def runner(command, **kwargs):
        observed["command"] = command
        observed["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "document_id": 42,
                    "version_id": "7",
                    "source_ref": "paperless/42/versions/7/synthetic.pdf",
                }
            ),
            stderr="",
        )

    result = module._run_skill_json(
        root,
        ["capture", "--document-id", "42", "--version-id", "7"],
        runner=runner,
    )
    assert observed["command"][1] == str(script)
    assert observed["command"][2:] == [
        "capture",
        "--document-id",
        "42",
        "--version-id",
        "7",
    ]
    assert "shell" not in observed["kwargs"]
    assert result["source_ref"].endswith("synthetic.pdf")
