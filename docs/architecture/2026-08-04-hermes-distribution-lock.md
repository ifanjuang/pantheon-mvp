# Hermes distribution composition lock

Date: 2026-08-04

Status: candidate implementation/deployment composition — non-authoritative.

## Purpose

The Hermes integration keeps independently owned components while recording one reproducible operational core:

```text
external run binding
bounded context bridge plugin
Runs API observer
```

Skills, policy MCP and dashboard remain available candidates in `Pantheon-Next`, but are not included in `pantheon-standard.lock.yaml` until explicitly selected. The lock is a composition, not a catalog.

## Integrity contract

The lock follows `pantheon.hermes_distribution_lock` revision 2.

It records:

- reviewed `Pantheon-Next` and `pantheon-mvp` source revisions;
- exact SHA-256 content digests for every selected component;
- deterministic `file` or `tree` digest modes;
- the exact reviewed Hermes target `0.20.0`;
- a nullable Hermes artifact digest while no real installation has been observed.

Repository refs provide provenance. Exact component identity is established by content digests because a lock stored inside `pantheon-mvp` cannot contain the future SHA of its own final commit.

```text
source revision recorded != final self-containing commit
component digest matched != component installed
runtime version reviewed != runtime artifact observed
```

## Hermes 0.20 placement

`Pantheon-Next/docs/governance/HERMES_V020_RUNTIME_SURFACE_REVIEW.md` owns the release-surface review. The official 0.20.0 release retains the Runs API used by the candidate bridge while adding broader runtime surfaces including A2A, outbound webhooks, grounded citations and voice.

Those surfaces are not included or activated by this distribution core:

```text
A2A peer trusted != approved actor
webhook available != external effect authorized
citation returned != Evidence admitted
voice instruction received != human approval recorded
provider/model request fields available != provider routing delegated to Pantheon
```

The run binding continues to omit `model`, `provider` and `model_options`; model and provider routing remain external Hermes configuration. No component digest changes because the selected implementation core is unchanged.

## Shared validator

`mvp_vertical/hermes_distribution.py` owns:

- schema validation;
- repository-root containment;
- deterministic file and tree digests;
- required core component checks;
- stable route checks;
- non-authority checks.

`tools/check_hermes_distribution_lock.py` remains a compatibility wrapper for CI. The architecture workflow validates against the exact `Pantheon-Next` schema revision recorded by the lock and publishes a factual JSON report.

## One-shot operator CLI

The packaged command is:

```text
pantheon-hermes
```

Supported operations:

```text
verify-distribution
observe
launch
reconcile
```

The CLI exposes existing bounded classes only. It owns no daemon, queue, scheduler, polling loop, automatic retry, provider router, model selection, installation, activation or approval.

`launch` performs one sequence:

```text
observe reviewed Hermes surface
→ reserve one admitted launch
→ submit one run
→ record the exact runtime start
→ exit
```

`reconcile` reads one launch receipt, observes the runtime once, records a terminal candidate when safely mappable and exits.

## Composed acceptance

`tests/test_hermes_distribution_acceptance.py` continues to join the real run binding and context bridge handlers with deterministic external fakes. Additional tests cover digest integrity, the one-shot CLI and the exact 0.20.0 target.

They explicitly preserve:

```text
automatic_retry_performed = false
provider_routing_performed = false
technical_receipt_is_evidence = false
result_accepted = false
evidence_admitted = false
project_mutated = false
```

## Remaining external operation

Repository tests do not prove a real Hermes installation. The operator runbook is owned in:

```text
Pantheon-Next/docs/install/HERMES_EXECUTION_BRIDGE_RUNBOOK.md
```

A real acceptance still requires the exact Hermes 0.20.0 artifact digest, plugin installation, tool-surface qualification, host `task_id/session_id` correlation, one human-admitted read-only run and verified rollback.

The candidate lock therefore retains:

```text
artifact_digest: null
installation_state: not_observed
activation_state: not_activated
task_authorization_state: not_authorized
acceptance_state: not_run
```

## Boundaries

```text
composition pinned != components installed
components installed != binding activated
acceptance passed != task authorized
launch reservation != runtime dispatch
runtime return != accepted result
runtime output != Evidence
```

The lock and CLI are not a runtime, installer, scheduler, queue, provider router, plugin manager, memory system, approval engine or source of truth.
