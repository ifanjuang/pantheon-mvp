# Cards-first Cockpit Candidate

Status: implemented external UI candidate — not adopted, not activated, not production-authorized.

This directory contains the first cards-first cockpit shell served at `/cockpit/`.
It composes the existing bounded Document, Knowledge and Work Issue projections.
It does not add a card database, approval engine, workflow engine, runtime,
provider router, external action path or memory promotion path.

```text
Pantheon Next governs.
Hermes executes explicit bounded handoffs.
The cockpit exposes projections.
The human decides.
```

## Card anatomy

Every rendered card keeps one stable anatomy:

```text
type lockup
compact title
three-second summary
primary signal
status and project context
responsibility indicators
reviewable detail view
```

The visual projection is derived from three independent inputs:

```text
object kind
+ current owner-defined status
+ recent event where the underlying projection exposes one
```

A card is not the underlying object and never owns its status.

## Current implemented families

- Project Document cards from `GET /v1/projects/{parent_project_id}/documents`.
- Knowledge cards from `GET /v1/projects/{parent_project_id}/knowledge`.
- Work Issue cards from `GET /v1/projects/{parent_project_id}/work-issues`.
- One local Questionnaire card used to test structured clarification UX.
- Proposal-only Effect cards from `POST /v1/projects/{parent_project_id}/effects/preview`.

The Work Issue route performs one exact `case_ref == parent_project_id` match. It
returns the existing governed aggregate, including comments, Hermes runs and
append-only events. It does not infer project membership, broaden scope, mutate
status or grant Hermes database authority.

Recent visual effects are derived from owner data:

- Document: recent extraction completion;
- Knowledge: current persisted creation/update timestamps and version;
- Work Issue: latest append-only issue event.

These effects orient attention only. They are not truth, approval, execution or
memory statuses.

## Deterministic rapprochement preview

The `Rapprochement` scene accepts one new information item and searches only the
opened project scope. Candidate objects are collected from the existing Document,
Knowledge and Work Issue projections. Matching uses explicit object references
first and bounded lexical overlap second.

The response exposes:

```text
candidate effect
candidate target or unclassified creation
matching score
confidence band
human-readable reasons
information digest
human confirmation requirement
```

Candidate effects are limited to:

```text
CREATE
UPDATE
SUPERSEDE
CONFLICT
```

The preview is deliberately incomplete as an execution path:

- no proposal persistence;
- no card or owner-object mutation;
- no apply endpoint;
- no semantic model call;
- no automatic choice when multiple candidates are close;
- no inference outside the exact project scope.

Lexical similarity is orientation, not evidence or truth. A later owner-specific
write path and authenticated human confirmation remain required.

The Questionnaire card is session-local. It does not submit, persist or apply
any effect. After the local summary, its answers may prefill the Rapprochement
form, but the preview still requires an explicit user action.

Not implemented in this lot:

- Situation persistence;
- owner-specific application of `CREATE`, `UPDATE`, `SUPERSEDE` or `CONFLICT`;
- Decision and Gate projection;
- Rite Review cards;
- Agora;
- authenticated human identity;
- card-event acknowledgement;
- Hermes handoff from cockpit interactions.

## CSS maintenance model

`styles/index.css` declares ordered cascade layers and imports bounded modules:

```text
tokens
foundations
layout
components
variants
effect preview module
motion
accessibility
```

HTML anatomy remains stable. The main renderer owns persisted-object cards;
`effects.js` owns only the proposal-only rapprochement scene and questionnaire
handoff. Colors and motion remain controlled by CSS variables and variants.

## Motion boundary

Motion is orientation-only:

- slow background gradient drift;
- one-shot recent-event sheen;
- restrained focus elevation;
- subtle human-attention pulse.

Motion never signifies approval, proof, successful execution or durable memory.
`prefers-reduced-motion` disables non-essential movement.
