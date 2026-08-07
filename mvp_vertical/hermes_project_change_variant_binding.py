"""One-shot Hermes binding for structured Project change alternatives.

This module extends the existing run-binding responsibility; it is not a fourth
distribution component. Launch delegates to :mod:`hermes_run_binding`. Terminal
reconciliation performs one status read and accepts only one closed JSON envelope
containing a typed Project change variant Execution Result.

Producing alternatives does not select one, create a ChangeCandidate, apply a
Project mutation, create a Decision, admit Evidence or authorize another task.
"""

from __future__ import annotations

import json
from typing import Any

from .hermes_run_binding import (
    MAX_RUNTIME_OUTPUT_CHARS,
    ExternalHermesRunBinding,
    HermesRunBindingError,
    HermesRunsHttpClient,
    PantheonRunBridgeClient,
    _as_text,
)

ENVELOPE_KIND = "pantheon_project_change_variants"
RESULT_KIND = "project_change_variant"


class HermesProjectChangeVariantBindingError(HermesRunBindingError):
    pass


class PantheonProjectChangeVariantBridgeClient(PantheonRunBridgeClient):
    """Use the existing return route with an optional typed Execution Result."""

    def record_variant_return(
        self,
        *,
        admission_id: str,
        run_id: str,
        expected_issue_version: int,
        normalized_return: dict[str, Any],
        result_candidate: dict[str, Any],
        execution_result: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/hermes/execution-admissions/{admission_id}/runs/{run_id}/return",
            body={
                "normalized_return": normalized_return,
                "result_candidate": result_candidate,
                "execution_result": execution_result,
                "expected_issue_version": expected_issue_version,
                "idempotency_key": idempotency_key,
            },
        )


def _structured_output(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        payload = value
    elif isinstance(value, str):
        if len(value) > MAX_RUNTIME_OUTPUT_CHARS:
            raise HermesProjectChangeVariantBindingError(
                f"Hermes runtime output exceeds {MAX_RUNTIME_OUTPUT_CHARS} characters"
            )
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise HermesProjectChangeVariantBindingError(
                "Hermes Project variant output must be one JSON object without prose or fences"
            ) from exc
    else:
        raise HermesProjectChangeVariantBindingError(
            "Hermes Project variant output must be a JSON object"
        )
    if not isinstance(payload, dict):
        raise HermesProjectChangeVariantBindingError(
            "Hermes Project variant output must be a JSON object"
        )
    unknown = set(payload) - {"kind", "summary", "execution_result"}
    if unknown:
        raise HermesProjectChangeVariantBindingError(
            "unsupported Project variant envelope field(s): " + ", ".join(sorted(unknown))
        )
    if payload.get("kind") != ENVELOPE_KIND:
        raise HermesProjectChangeVariantBindingError(
            f"Hermes Project variant output kind must be {ENVELOPE_KIND}"
        )
    summary = str(payload.get("summary") or "").strip()
    if not summary:
        raise HermesProjectChangeVariantBindingError(
            "Hermes Project variant output summary is required"
        )
    execution_result = payload.get("execution_result")
    if not isinstance(execution_result, dict):
        raise HermesProjectChangeVariantBindingError(
            "Hermes Project variant output requires execution_result"
        )
    return {
        "kind": ENVELOPE_KIND,
        "summary": summary,
        "execution_result": execution_result,
    }


def _variant_result_refs(execution_result: dict[str, Any]) -> list[str]:
    items = execution_result.get("results")
    if not isinstance(items, list) or not items:
        raise HermesProjectChangeVariantBindingError(
            "Project variant Execution Result must contain alternatives"
        )
    refs: list[str] = []
    labels: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or item.get("result_kind") != RESULT_KIND:
            raise HermesProjectChangeVariantBindingError(
                "Project variant Execution Result accepts only project_change_variant items"
            )
        result_id = str(item.get("result_id") or "").strip()
        payload = item.get("payload")
        if not result_id or not isinstance(payload, dict):
            raise HermesProjectChangeVariantBindingError(
                "every Project variant result requires an identity and payload"
            )
        label = str(payload.get("variant_label") or "").strip()
        if not label or label in labels:
            raise HermesProjectChangeVariantBindingError(
                "Project variant labels must be non-empty and unique"
            )
        labels.add(label)
        refs.append(result_id)
    if len(refs) < 2:
        raise HermesProjectChangeVariantBindingError(
            "Project variant comparison requires at least two alternatives"
        )
    if len(set(refs)) != len(refs):
        raise HermesProjectChangeVariantBindingError(
            "Project variant result identities must be unique"
        )
    return refs


class ExternalHermesProjectChangeVariantBinding:
    """Launch normally, then reconcile one structured variant result once."""

    def __init__(
        self,
        *,
        observer: Any,
        pantheon: PantheonProjectChangeVariantBridgeClient,
        hermes: HermesRunsHttpClient,
    ) -> None:
        self._pantheon = pantheon
        self._hermes = hermes
        self._launch_binding = ExternalHermesRunBinding(
            observer=observer,
            pantheon=pantheon,
            hermes=hermes,
        )

    def launch(self, *, admission_id: str, idempotency_key: str) -> dict[str, Any]:
        return self._launch_binding.launch(
            admission_id=admission_id,
            idempotency_key=idempotency_key,
        )

    def reconcile_once(
        self,
        *,
        launch_receipt: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        admission_id = str(launch_receipt.get("admission_id") or "").strip()
        run_id = str(launch_receipt.get("run_id") or "").strip()
        expected_version = launch_receipt.get("return_expected_issue_version")
        if not admission_id or not run_id or not isinstance(expected_version, int):
            raise HermesProjectChangeVariantBindingError(
                "launch receipt is incomplete for Project variant reconciliation"
            )

        status = self._hermes.get_status(run_id)
        runtime_status = str(status.get("status") or "").strip().lower()
        if runtime_status in {"started", "running", "stopping", "pending"}:
            return {
                "kind": "hermes_project_change_variant_reconciliation",
                "run_id": run_id,
                "runtime_status": runtime_status,
                "pantheon_return_recorded": False,
                "execution_result_stored": False,
                "variant_selected": False,
                "scheduler_effect": False,
                "retry_effect": False,
            }
        if runtime_status == "cancelled":
            return {
                "kind": "hermes_project_change_variant_reconciliation",
                "run_id": run_id,
                "runtime_status": runtime_status,
                "pantheon_return_recorded": False,
                "execution_result_stored": False,
                "variant_selected": False,
                "reason": "cancelled has no governed Project variant return mapping",
                "scheduler_effect": False,
                "retry_effect": False,
            }
        if runtime_status == "failed":
            detail = _as_text(status.get("error") or status.get("output") or "Hermes run failed.")
            recorded = self._pantheon.record_return(
                admission_id=admission_id,
                run_id=run_id,
                expected_issue_version=expected_version,
                normalized_return={
                    "outcome": "failed",
                    "summary": detail[:20_000] or "Hermes run failed.",
                    "trace_refs": [f"hermes://runs/{run_id}"],
                    "result_refs": [],
                    "evidence_candidate_refs": [],
                },
                result_candidate=None,
                idempotency_key=f"{idempotency_key}:return",
            )
            return {
                "kind": "hermes_project_change_variant_reconciliation",
                "run_id": run_id,
                "runtime_status": runtime_status,
                "pantheon_return_recorded": True,
                "execution_result_stored": False,
                "variant_selected": False,
                "project_mutated": False,
                "decision_created": False,
                "evidence_admitted": False,
                "external_effect_authorized": False,
                "scheduler_effect": False,
                "retry_effect": False,
                "recorded": recorded,
            }
        if runtime_status != "completed":
            return {
                "kind": "hermes_project_change_variant_reconciliation",
                "run_id": run_id,
                "runtime_status": runtime_status or "unknown",
                "pantheon_return_recorded": False,
                "execution_result_stored": False,
                "variant_selected": False,
                "reason": "runtime status is not mapped by this bounded reconciliation",
                "scheduler_effect": False,
                "retry_effect": False,
            }

        envelope = _structured_output(status.get("output"))
        execution_result = envelope["execution_result"]
        result_refs = _variant_result_refs(execution_result)
        execution_result_id = str(
            execution_result.get("execution_result_id") or ""
        ).strip()
        if not execution_result_id:
            raise HermesProjectChangeVariantBindingError(
                "Project variant Execution Result identity is required"
            )

        result_candidate = {
            "result_type": "project_change_variant_execution_result",
            "candidate_payload": {
                "execution_result_id": execution_result_id,
                "result_refs": result_refs,
                "variant_count": len(result_refs),
                "runtime_status": runtime_status,
            },
            "confidence_note": None,
            "known_limits": [
                "Alternatives are unselected and have not changed the Project.",
                "Compatibility findings remain candidates for human review.",
            ],
            "open_questions": [],
            "source_refs": [],
            "missing_evidence": [],
        }
        normalized = {
            "outcome": "result_candidate",
            "summary": envelope["summary"][:20_000],
            "trace_refs": [f"hermes://runs/{run_id}"],
            "result_refs": result_refs,
            "evidence_candidate_refs": [],
        }
        recorded = self._pantheon.record_variant_return(
            admission_id=admission_id,
            run_id=run_id,
            expected_issue_version=expected_version,
            normalized_return=normalized,
            result_candidate=result_candidate,
            execution_result=execution_result,
            idempotency_key=f"{idempotency_key}:return",
        )
        return {
            "kind": "hermes_project_change_variant_reconciliation",
            "run_id": run_id,
            "runtime_status": runtime_status,
            "pantheon_return_recorded": True,
            "execution_result_stored": recorded.get("execution_result_stored") is True,
            "execution_result_id": execution_result_id,
            "project_change_variant_count": len(result_refs),
            "result_refs": result_refs,
            "variant_selected": False,
            "project_mutated": False,
            "decision_created": False,
            "evidence_admitted": False,
            "external_effect_authorized": False,
            "technical_receipt_is_evidence": False,
            "scheduler_effect": False,
            "retry_effect": False,
            "recorded": recorded,
            "non_equivalences": [
                "runtime completed != alternatives selected",
                "Execution Result stored != ChangeCandidate created",
                "variant produced != Project mutated",
                "technical receipt != Evidence",
            ],
        }
