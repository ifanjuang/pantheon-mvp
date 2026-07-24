# Synthetic document runtime check

Status: operator acceptance candidate — implemented helper / not run on a target deployment.

This procedure is for a synthetic deployment fixture only. It is not authorized for a real professional dossier.

## Phase 1 — read-only observation

Run the helper with the observer URL and Cockpit read key available in the environment:

```bash
python scripts/document_runtime_synthetic_check.py \
  --observer-url http://document-runtime-observer:8083
```

Expected bounded result:

```text
candidate_ready_for_synthetic_intake = true | false
production_authorization = false
technical_receipt_is_evidence = false
```

The four prerequisites remain independent:

```text
Paperless source path reachable
Pantheon PDP ready observed
Docling health endpoint reachable
pantheon-document-intake listed by Hermes native inventory
```

A failed prerequisite is not automatically a safety judgment. It is a technical observation to diagnose at its source.

## Phase 2 — optional synthetic intake

This step creates candidate state in the MVP store and therefore is never implicit.

Prerequisites:

1. a synthetic document already exists in the non-production Paperless instance;
2. its exact version id is known;
3. a synthetic Task Contract contains the exact `source_ref` returned by capture;
4. a decision payload is explicitly provided for the synthetic test;
5. `MVP_HERMES_API_KEY` is available in the operator environment;
6. the installed Hermes skill package is present under `~/.hermes/skills/pantheon-document-intake` or supplied via `--skill-root`.

Run:

```bash
python scripts/document_runtime_synthetic_check.py \
  --observer-url http://document-runtime-observer:8083 \
  --run-intake \
  --ack SYNTHETIC_ONLY \
  --document-id 42 \
  --version-id 7 \
  --contract /path/to/synthetic-task-contract.yaml \
  --decision /path/to/synthetic-decision.json
```

The helper first executes the installed skill transport's exact `capture` operation. It then refuses to continue unless the Task Contract explicitly contains `synthetic` and the exact returned `source_ref`.

Only then may it execute the installed skill transport's `intake` operation.

## Expected boundaries

The synthetic helper never performs:

```text
Paperless upload
Paperless metadata mutation
delete
version replacement
Knowledge publication
Evidence admission
activation
installation
update
external send
```

A successful receipt remains a technical trace:

```text
runtime_success != Evidence
synthetic check pass != production adoption
installed skill transport success != Hermes agent selection proven
validated decision fields != authenticated human issuer
```

The unresolved human-issuer authentication proof gap remains OPEN even when the synthetic intake succeeds.
