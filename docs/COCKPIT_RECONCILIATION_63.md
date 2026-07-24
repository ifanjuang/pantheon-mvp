# Cockpit reconciliation after MVP #63

Status: reconciled contract note. This note does not establish deployment, adoption, activation or production authorization.

The five-space Cockpit remains:

```text
Pantheon
Affaires
Connaissances
Outils
Décisions
```

## Reconciliation with main

`mvp_vertical.capability_manager` on current `main` now includes `HermesCapabilityExecutor` in addition to the bounded lifecycle manager.

Therefore the Outils contract is refined as follows:

```text
Capability lifecycle manager     implemented
Hermes native executor adapter   implemented / native operations path to verify against real Hermes 0.19
Cockpit CapabilityRecord API     not exposed
Cockpit live inventory           not connected
live Hermes endpoint             not configured by repository state
installation / enable / update   governed backend path exists; Cockpit mutation binding absent
activation for project scope     not established
production authorization         false / not granted
```

The UI must continue to keep mutation controls disabled until an owner API exposes current `CapabilityRecord` observations and the consequential action can be bound to Pantheon preflight + valid human Decision + the native Hermes executor.

```text
implemented executor != connected runtime
installed != approved
enabled != activated for a scope
healthy != safe
update_available != update_authorized
technical receipt != Evidence
```

## Stacked document-runtime candidates

MVP #59, #61 and #62 are stacked candidate branches rather than current `main`. They may enrich Outils once adopted/merged, but this five-space branch must not present them as current live state.

Target read-only Outils cards when those bindings are adopted:

- Document Runtime Status;
- Paperless/gateway observation;
- Pantheon PDP observation;
- Docling observation;
- Hermes native skill inventory observation;
- synthetic acceptance status.

Each observation keeps its own source and timestamp. No global `healthy=true` is synthesized.

## Responsibility split

```text
Pantheon governs status, scope, gates, activation and consequential decisions.
Hermes performs the bounded native capability operation when authorized.
OpenWebUI/Cockpit displays observations and captures bounded intent.
Human approves consequential effects.
Forbidden: Cockpit self-approval, silent install/update/activation, inference of safety from health, promotion of technical receipts to Evidence.
```
