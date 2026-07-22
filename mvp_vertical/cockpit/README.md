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

The Questionnaire card is session-local. It does not submit, persist or apply
`CREATE`, `UPDATE`, `SUPERSEDE` or `CONFLICT` effects. Its detail view says so
explicitly.

Not implemented in this lot:

- Situation persistence;
- Decision and Gate projection;
- Rite Review cards;
- Agora;
- deterministic information-to-object rapprochement;
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
motion
accessibility
```

HTML anatomy remains stable. JavaScript sets only semantic data attributes such
as `data-kind`, `data-status`, `data-event` and `data-attention`. Colors and
motion are owned by CSS variables and variants.

## Motion boundary

Motion is orientation-only:

- slow background gradient drift;
- one-shot recent-event sheen;
- restrained focus elevation;
- subtle human-attention pulse.

Motion never signifies approval, proof, successful execution or durable memory.
`prefers-reduced-motion` disables non-essential movement.
