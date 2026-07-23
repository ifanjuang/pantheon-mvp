---
name: pantheon-document-intake
description: "Intake governed Paperless documents into Pantheon."
version: 0.1.0
author: IFJ Architecture
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [pantheon, paperless, documents, intake, governance]
    category: productivity
    related_skills: []
---

# Pantheon Document Intake Skill

Use this skill to inspect Paperless-ngx sources and, when a valid Task Contract and human decision exist, ask the bounded Pantheon gateway to create a Project Document candidate through the existing Docling/store ingestion path.

The skill is an external Hermes execution adapter. It is not Pantheon authority and it contains no Paperless credential, policy engine, approval logic, Knowledge promotion or Evidence admission logic.

## When to Use

Use this skill when the user asks to:

- find or inspect a professional document stored in the reviewed Paperless runtime;
- inspect the exact version, digest and source identity of a Paperless document;
- intake an exact Paperless version into a Pantheon project under a Task Contract;
- observe a Paperless native task result;
- apply a separately authorized operational metadata mirror after review.

Do not use it to silently broaden project scope, infer that the latest Paperless version is the approved source, publish Knowledge automatically, admit Evidence, delete/replace documents, change permissions, enable Paperless AI/remote OCR, or promote memory.

## Prerequisites

The runtime must provide:

```text
PANTHEON_PAPERLESS_GATEWAY_URL
MVP_HERMES_API_KEY
```

`MVP_HERMES_API_KEY` must come from the runtime secret store. Never print it, place it in a prompt, pass it as a CLI argument, persist it in a Task Contract, or return it in an artifact.

The server-side gateway separately owns:

```text
PAPERLESS_API_TOKEN
PANTHEON_POLICY_API_KEY
```

Hermes must not receive or forward those secrets through this skill.

For binary/office document intake, the external runtime must also have the reviewed Docling Serve binding configured. The gateway owns that connection.

## How to Run

Use the bundled transport script through the native Hermes terminal tool. In the default Hermes skill installation layout:

```bash
SKILL_ROOT="${HERMES_HOME:-$HOME/.hermes}/skills/pantheon-document-intake"
python3 "$SKILL_ROOT/scripts/pantheon_document_intake.py" --help
```

When a profile or custom skill directory is active, resolve the actual installed skill location instead of assuming the default path.

Do not reconstruct the Paperless or Pantheon HTTP calls manually when the bundled client can perform them. The gateway is the reviewed secret and policy boundary.

## Quick Reference

Read-only operations:

```bash
python3 "$SKILL_ROOT/scripts/pantheon_document_intake.py" search --query "CCTP charpente"
python3 "$SKILL_ROOT/scripts/pantheon_document_intake.py" inspect --document-id 42
python3 "$SKILL_ROOT/scripts/pantheon_document_intake.py" capture --document-id 42 --version-id 7
python3 "$SKILL_ROOT/scripts/pantheon_document_intake.py" task --task-id <paperless-task-id>
```

Governed Project Document intake:

```bash
python3 "$SKILL_ROOT/scripts/pantheon_document_intake.py" intake \
  --document-id 42 \
  --version-id 7 \
  --contract /path/to/task-contract.yaml \
  --decision /path/to/human-decision.json
```

Governed operational metadata mirror:

```bash
python3 "$SKILL_ROOT/scripts/pantheon_document_intake.py" update-metadata \
  --document-id 42 \
  --changes /path/to/changes.json \
  --decision /path/to/human-decision.json \
  --candidate /path/to/effect-candidate.json
```

## Procedure

### 1. Inspect before acting

Search or inspect the Paperless document first. Treat returned metadata and OCR/search text as operational observations only.

```text
Paperless metadata != canonical business classification
Paperless OCR != source truth
Paperless search hit != Evidence
Paperless task success != professional validation
```

### 2. Freeze an exact source version

Before intake, use `capture` with an explicit Paperless `version-id`.

Record the returned candidate identity:

```text
document_id
version_id
original_filename
content_hash
storage_reference
source_ref
```

Never substitute a mutable "latest" pointer for the exact version required by the Task Contract.

### 3. Check the Task Contract perimeter

The Task Contract must explicitly declare the exact generated `source_ref`, for example:

```text
paperless/42/versions/7/CCTP-charpente.pdf
```

If it does not, stop and return a scope gap. Do not edit, widen or regenerate the Task Contract merely to make the source fit.

### 4. Check the human decision reference

A governed intake requires a human decision reference covering the exact effect.

The gateway binds validation to facts it derives itself:

```text
required approval ceiling <- Task Contract
required scope            <- Task Contract
object identity           <- exact Paperless version + Task Contract
expected digest           <- exact source capture + Task Contract digest
```

Caller-supplied `expectation` values cannot weaken those requirements.

If the decision does not match the derived scope/object/digest/ceiling, the effect is blocked. Do not replace it with Hermes smart approval, `/yolo`, model judgment or a fabricated human identity.

### 5. Run governed intake

Call `intake` only after steps 1–4.

The gateway performs:

```text
exact Paperless capture
-> Task Contract scope check
-> Pantheon preflight
-> human decision validation
-> existing store.ingest
-> Docling/direct conversion
-> Project Document candidate + extraction/chunks
-> paperless_source_bindings
```

The result remains bounded:

```text
Project Document candidate != Knowledge Item
Source Capture != Evidence
runtime success != professional validation
```

### 6. Treat blocked results as outcomes

When the gateway returns `status: blocked`, report the disposition and reasons. Do not retry through another write path, direct Paperless credentials, direct database access, a shell workaround, or an ungoverned HTTP call.

Typical next actions are human review, Task Contract revision by the proper governance path, evidence collection, or waiting for the policy service to recover.

### 7. Keep Knowledge separate

This skill does not publish Knowledge. If the user requests Knowledge publication, use the existing governed Knowledge path after Project Document intake and preserve the source/extraction provenance.

Do not use Paperless tags or custom fields as a substitute for Pantheon project links or Knowledge records.

## Pitfalls

- Do not call Paperless directly from the skill; the token belongs server-side.
- Do not treat a successful Paperless task as proof.
- Do not derive project scope from Paperless tags.
- Do not send a different version than the one declared by the Task Contract.
- Do not silently fall back to NAS or another DMS when Paperless is unavailable.
- Do not use `update-metadata` without an effect candidate that carries the governed scope and decision expectation required by the workflow.
- Do not enable Paperless AI, external LLMs, remote OCR, webhooks or additional provider paths as part of this skill.
- Do not use Hermes cron, background work, queues or gateways to bypass an unresolved gate.
- Do not retain source content or human decisions in Hermes memory merely because the skill observed them.

## Verification

A successful read proves only that the gateway and Paperless were reachable for that request.

A successful governed intake should return, at minimum:

```text
status: applied
effect_ran: true
operation: project_document_intake
task_contract_ref
source_ref
source_content_hash
decision_expectation
knowledge_published: false
evidence_admitted: false
```

Before relying on a live deployment, verify separately:

```text
Paperless image/version observed
Paperless gateway reachable on the intended private path
Hermes key accepted without exposing the Paperless token
Pantheon PDP reachable
blocked decision test prevents the intake executor from running
wrong source_ref is refused before policy/execution
wrong object/digest/scope is refused after PEP binding
Docling conversion works for a synthetic source
rollback target exists
```

These checks do not establish production approval.
