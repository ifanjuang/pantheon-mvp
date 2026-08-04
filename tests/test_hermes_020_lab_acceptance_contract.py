from __future__ import annotations

import ast
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "hermes-020-lab-acceptance.yml"
HARNESS = ROOT / "tools" / "run_hermes_020_lab_acceptance.py"
FIXTURE = ROOT / "tools" / "hermes_020_lab_fixture.py"


def test_lab_acceptance_is_explicit_pinned_and_ephemeral() -> None:
    raw = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.safe_load(raw)

    assert workflow["name"] == "Hermes 0.20.0 Lab Acceptance"
    assert "workflow_dispatch" in workflow[True]
    job = workflow["jobs"]["ephemeral-lab"]
    assert job["runs-on"] == "ubuntu-24.04"
    assert job["timeout-minutes"] == 35

    env = job["env"]
    assert env["HERMES_RELEASE_COMMIT"] == "3c27eb6234bf91b8ceee9e9071591b31e9b148cb"
    assert env["HERMES_VERSION"] == "0.20.0"
    assert env["PANTHEON_NEXT_REF"] == "db5506668f06bab05b0cad1b244ff19ab17b5f52"
    assert env["HERMES_API_BASE"].endswith("/p/pantheon-governed")
    assert "secrets." not in raw
    assert "self-hosted" not in raw
    assert "artifact_digest:" not in raw
    assert "status: observed" not in raw
    assert "status: qualified" not in raw


def test_lab_acceptance_keeps_install_activation_run_and_rollback_separate() -> None:
    raw = WORKFLOW.read_text(encoding="utf-8")

    install = raw.index("plugins install")
    inspect = raw.index("plugins list")
    enable = raw.index("plugins enable")
    observe = raw.index("pantheon-hermes\" observe")
    launch = raw.index("pantheon-hermes\" launch")
    reconcile = raw.index("pantheon-hermes\" reconcile")
    disable = raw.index("plugins disable")

    assert install < inspect < enable < observe < launch < reconcile < disable
    assert "--no-enable" in raw
    assert raw.count("capture-memory-status") == 3
    assert "--expected-profile \"$PROFILE\"" in raw
    assert "--memory-status-receipt" in raw
    assert raw.count("--allowed-tool pantheon_context_manifest") == 2
    assert raw.count("--allowed-tool pantheon_context_entity") == 2
    assert "profile route remained reachable after gateway rollback" in raw


def test_harness_fails_closed_and_does_not_claim_target_acceptance() -> None:
    raw = HARNESS.read_text(encoding="utf-8")
    ast.parse(raw)

    assert '"status": "passed"' in raw
    assert '"target_installation_observed": False' in raw
    assert '"production_activated": False' in raw
    assert '"future_tasks_authorized": False' in raw
    assert '"result_accepted": False' in raw
    assert '"evidence_admitted": False' in raw
    assert "set(tool_surface.get(\"active_tools\") or []) == EXPECTED_TOOLS" in raw
    assert "session_memory_header_present" in raw
    assert "X-Hermes-Session-Key was observed" in raw
    assert "This qualifies an ephemeral GitHub-hosted laboratory installation only." in raw


def test_fixture_is_local_bounded_and_exercises_context_refusal() -> None:
    raw = FIXTURE.read_text(encoding="utf-8")
    ast.parse(raw)

    assert 'default="127.0.0.1"' in raw
    assert "ThreadingHTTPServer" in raw
    assert "pantheon_context_manifest" in raw
    assert "pantheon_context_entity" in raw
    assert "project-outside" in raw
    assert "entity is outside the admitted Context Pack" in raw
    assert "LAB_ACCEPTANCE_COMPLETED" in raw
    assert '"evidence_admitted": False' in raw
    assert '"result_accepted": False' in raw
    assert '"project_mutated": False' in raw
    assert "requests" not in raw
    assert "subprocess" not in raw
