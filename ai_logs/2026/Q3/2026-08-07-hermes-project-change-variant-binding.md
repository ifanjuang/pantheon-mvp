# Hermes Project change variant binding

Date: 2026-08-07
Status: G2 implementation candidate; checks and real Hermes 0.20.0 laboratory pending.

## Objective

Complete tranche G by producing the merged `project_change_variant` contract through
the existing external Hermes run binding, retaining the typed Execution Result under
the consumed admission, and exposing a separate human selection route.

The binding must not select an alternative, create a ChangeCandidate automatically,
apply a Project mutation, create a Decision, admit Evidence or authorize a follow-up.

## Existing responsibilities reused

```text
ExternalHermesRunBinding
-> one-shot qualification, launch reservation, run submission and start record.

Hermes runtime return route
-> admission-bound transactional return normalization.

Execution Results
-> immutable project_change_variant persistence.

project_change_variants
-> separate human selection into the existing ChangeCandidate owner.
```

G2 remains part of the existing `run-binding` distribution component. No fourth
component, scheduler, queue, polling loop, automatic retry or provider router is
introduced.

## Structured return contract

The specialized reconciliation accepts only one JSON object without prose or code
fences:

```json
{
  "kind": "pantheon_project_change_variants",
  "summary": "...",
  "execution_result": {}
}
```

The Execution Result must contain at least two unique `project_change_variant`
alternatives. Malformed output, another envelope kind, one alternative, duplicate
labels or another result kind is refused before the Pantheon return write.

## Server-side admission checks

The Pantheon return validates:

- exact Task Contract identity against the consumed admission;
- exact admitted Project identity;
- only Project change variant result kinds;
- unique result identities;
- payload Project consistency;
- every basis reference inside the immutable Context Pack;
- exact vendored candidate schema during Execution Result persistence.

The typed Execution Result and generic Hermes ResultCandidate are stored inside the
same return transaction. An out-of-scope basis, stale Work Issue version or
idempotency conflict retains neither record and leaves the run unreturned.

## Human selection surface

A separate editor-key route requires `X-Pantheon-Human-Actor` and an idempotency
key. It calls the G1 transition and returns a pending existing ChangeCandidate.
The response explicitly keeps Project mutation, Decision, Evidence, memory and
external-effect posture false.

## Hermes 0.20.0 laboratory

A G2 overlay reuses the already accepted F laboratory installation and rollback:

- exact upstream commit `3c27eb6234bf91b8ceee9e9071591b31e9b148cb`;
- isolated Hermes 0.20.0 installation;
- existing three-component distribution;
- progressive discovery of the two admitted context tools;
- manifest and admitted Project reads;
- outside Project refusal;
- final structured production of zinc and slate alternatives;
- specialized one-shot reconciliation;
- plugin disable and gateway rollback.

The variant laboratory is separate from the already merged F acceptance and does
not rewrite its evidence.

## Required completion checks

```text
unit binding tests
PostgreSQL transactional return tests
human selection API tests
Pantheon Architecture Audit
contract-tests
full PostgreSQL suite
real Hermes 0.20.0 Project Variant Lab
```

## Non-equivalences

```text
runtime completed != alternatives selected
Execution Result stored != ChangeCandidate created
variant selected != Project mutation applied
technical receipt != Evidence
lab acceptance != agency/NAS activation
```
