from __future__ import annotations

import pytest

from mvp_vertical.runtime_profile import (
    RuntimeProfileValidationError,
    normalize_runtime_observation,
    normalize_runtime_profile,
)


def test_normalize_runtime_profile_preserves_release_specific_capabilities() -> None:
    profile = normalize_runtime_profile(
        {
            "runtime_id": "hermes_agent_runtime",
            "binding_id": "nousresearch_hermes_agent",
            "runtime_version": "v2026.8.3",
            "api_version": "observed",
            "observed_at": "2026-08-03T18:00:00Z",
            "observed_by": "hermes_adapter",
            "compatibility_status": "compatible",
            "capabilities": {
                "background_execution": {"support": "reported"},
                "parallel_delegation": {"support": "observed", "max_workers": 4},
            },
            "source_refs": ["https://github.com/NousResearch/hermes-agent/releases/tag/v2026.8.3"],
        }
    )

    assert profile["compatibility_status"] == "compatible"
    assert profile["capabilities"]["parallel_delegation"]["max_workers"] == 4
    assert "authorization_status" not in profile
    assert "evidence_status" not in profile


def test_runtime_profile_rejects_invalid_support_state() -> None:
    with pytest.raises(RuntimeProfileValidationError, match="unsupported support state"):
        normalize_runtime_profile(
            {
                "runtime_id": "runtime",
                "binding_id": "binding",
                "runtime_version": "1",
                "observed_at": "2026-08-03T18:00:00Z",
                "observed_by": "adapter",
                "capabilities": {"learning": {"support": "authorized"}},
            }
        )


def test_runtime_profile_rejects_missing_observation_time() -> None:
    with pytest.raises(RuntimeProfileValidationError, match="observed_at"):
        normalize_runtime_profile(
            {
                "runtime_id": "runtime",
                "binding_id": "binding",
                "runtime_version": "1",
                "observed_by": "adapter",
            }
        )


def test_normalize_runtime_observation_is_not_evidence() -> None:
    observation = normalize_runtime_observation(
        {
            "observation_id": "obs-1",
            "runtime_id": "hermes_agent_runtime",
            "runtime_version": "v2026.8.3",
            "run_id": "run-1",
            "kind": "completed",
            "observed_at": "2026-08-03T18:05:00+00:00",
            "payload": {"result_candidate_id": "candidate-1"},
            "trace_refs": ["trace-1"],
        }
    )

    assert observation["kind"] == "completed"
    assert observation["payload"]["result_candidate_id"] == "candidate-1"
    assert "evidence" not in observation
    assert "accepted" not in observation


def test_runtime_observation_rejects_authority_like_kind() -> None:
    with pytest.raises(RuntimeProfileValidationError, match="unsupported runtime observation kind"):
        normalize_runtime_observation(
            {
                "observation_id": "obs-1",
                "runtime_id": "runtime",
                "runtime_version": "1",
                "run_id": "run-1",
                "kind": "approved",
                "observed_at": "2026-08-03T18:05:00Z",
            }
        )
