# Document runtime live observations

Status: external executable candidate — source-attributed read-only observation implemented / not deployed or adopted.

This slice extends the first Document Runtime Status card without turning the Cockpit, Paperless gateway or Pantheon into a runtime manager.

```text
OpenWebUI exposes observations.
External observer reads bounded technical surfaces.
Hermes native CLI supplies its own skill inventory when co-located.
Pantheon PDP supplies policy readiness/meta observations.
Docling supplies its own health-endpoint observation.
Pantheon governs status and activation.
Human decides consequential activation.
```

## Implemented observer

`mvp_vertical.document_runtime_observer` exposes:

```text
GET /health
GET /v1/document-runtime/observations
```

`/health` means only that the observer process answers.

`/v1/document-runtime/observations` is protected by the Cockpit read key and returns four independent observations.

### Paperless / bounded gateway

Source:

```text
GET <PANTHEON_PAPERLESS_GATEWAY_URL>/health
```

Observed fields include gateway reachability, Paperless reachability and the declared intake/write surfaces.

```text
Paperless reachable != Paperless healthy
Paperless healthy != safe
```

### Pantheon PDP

Source:

```text
GET <PANTHEON_POLICY_API_URL>/readyz
GET <PANTHEON_POLICY_API_URL>/v1/meta
```

The policy credential remains server-side. The returned projection allowlists only bounded meta fields such as contract/source mode/repository version and commit.

```text
PDP ready != effect authorized
PDP reachable != policy decision for a concrete effect
```

The current V0 external/canonical effect flags remain evaluated at effect preflight time; this status surface does not synthesize them.

### Docling Serve

Source:

```text
GET <DOCLING_SERVE_URL>/health
```

An optional Docling API key is sent server-side when configured.

```text
Docling health endpoint responds != extraction quality established
Docling reachable != professional validation
```

### Hermes native skill inventory

Source when the observer is explicitly configured on the Hermes host:

```text
hermes skills list
```

The command is fixed and executed without a shell. The output is checked for the exact skill token:

```text
pantheon-document-intake
```

Possible installation observations:

```text
installed_observed
not_listed_observed
not_observed
```

Default mode is `disabled`, which returns `not_observed` rather than guessing that the skill is absent.

```text
skill listed != approved
skill listed != activated for a project scope
skill listed != model invoked the skill
```

## Cockpit projection

`openwebui/pantheon_document_runtime_live_status.py` reads only the bounded observer endpoint with the Cockpit read key.

The OpenWebUI Tool does not receive:

```text
PAPERLESS_API_TOKEN
PANTHEON_POLICY_API_KEY
MVP_HERMES_API_KEY
DOCLING_SERVE_API_KEY
Paperless database credentials
```

It renders the observations source-by-source and intentionally does not calculate a global `healthy=true` result.

```text
synthetic_global_health = not_computed
write_effect = false
authority_effect = none
activation_changed = false
```

## Synthetic deployment check

`scripts/document_runtime_synthetic_check.py` is an operator-run acceptance helper. It is not a scheduler, monitor, approval engine or production health authority.

Default mode is read-only. It checks that the independent observations show:

```text
Paperless source path reachable
Pantheon PDP ready endpoint observed
Docling health endpoint reachable
pantheon-document-intake listed by native Hermes inventory
```

A pass means only:

```text
candidate_ready_for_synthetic_intake = true
```

It does not mean safe, approved or production-ready.

### Optional synthetic intake

A state-writing intake requires all of the following explicit inputs:

```text
--run-intake
--ack SYNTHETIC_ONLY
exact Paperless document id
exact Paperless version id
synthetic Task Contract
human decision payload
installed Hermes skill transport
MVP_HERMES_API_KEY in the operator environment
```

The helper first uses the installed skill transport to inspect the exact Source Capture. It refuses the intake unless:

- the Task Contract explicitly contains `synthetic`;
- the exact observed `source_ref` is present in that Task Contract;
- all four runtime observations satisfy the bounded synthetic prerequisites.

It then calls the installed `pantheon-document-intake` transport script. It does not recreate gateway/PDP logic locally.

The helper never performs:

```text
Paperless upload
Paperless metadata mutation
delete or version replacement
Knowledge publication
Evidence admission
activation/update/install
provider routing
```

The receipt always declares:

```text
technical_receipt_is_evidence = false
human_issuer_authentication_proven = false
activation_changed = false
production_authorization = false
```

When the optional intake succeeds, it additionally declares:

```text
agent_skill_selection_proven = false
```

because an operator invoking the installed transport script is not proof that the Hermes agent/model selected the skill in a normal conversation.

## Configuration

Observer server-side configuration:

```text
MVP_COCKPIT_API_KEY
PANTHEON_PAPERLESS_GATEWAY_URL
PANTHEON_POLICY_API_URL
PANTHEON_POLICY_API_KEY
DOCLING_SERVE_URL
DOCLING_SERVE_API_KEY              optional
MVP_HERMES_INVENTORY_MODE          disabled | local_cli
HERMES_CLI_PATH                    fixed executable path/name
MVP_RUNTIME_OBSERVER_TIMEOUT
```

OpenWebUI configuration:

```text
observer URL
MVP_COCKPIT_API_KEY
```

Synthetic operator configuration additionally uses `MVP_HERMES_API_KEY` only when the operator explicitly requests the synthetic intake.

## Current status

```text
Paperless observation source       implemented candidate
Pantheon PDP observation           implemented candidate
Docling health observation         implemented candidate
Hermes native inventory observer   implemented candidate / co-location required
OpenWebUI live status projection   implemented candidate
synthetic read-only assessment     implemented candidate
optional synthetic intake helper  implemented candidate / not run
live target deployment             not established
live observations                  not established by repository tests
Hermes agent skill selection       not proven
human issuer authentication        not proven
adoption                           not decided
activation                         not authorized
production                         forbidden pending separate review
```
