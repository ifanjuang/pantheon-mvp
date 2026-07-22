# Cards-first Cockpit Candidate

Status: implemented external UI and bounded write candidate — not adopted, not activated, not production-authorized.

This directory contains the first cards-first cockpit shell served at `/cockpit/`.
It composes the existing bounded Document, Knowledge and Work Issue projections.
It does not add a card database, approval engine, workflow engine, runtime,
provider router, external action path or memory promotion path.

```text
Pantheon Next governs.
Hermes executes explicit bounded handoffs.
The cockpit exposes projections and narrow owner actions.
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
- One owner-specific Knowledge `UPDATE` gate with signed diff and explicit human confirmation.

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

The generic preview remains deliberately incomplete as an execution path:

- no proposal persistence;
- no card or owner-object mutation;
- no generic apply endpoint;
- no semantic model call;
- no automatic choice when multiple candidates are close;
- no inference outside the exact project scope.

Lexical similarity is orientation, not evidence or truth.

## First owner-specific Knowledge UPDATE

Only a candidate `UPDATE` whose exact target is an existing Knowledge item may
enter the first write gate. The gate uses two separate routes:

```text
POST /v1/projects/{project}/knowledge/{knowledge}/updates/preview
POST /v1/projects/{project}/knowledge/{knowledge}/updates/apply
```

The routes are disabled unless the runtime supplies a separate server-only secret:

```text
MVP_UPDATE_SIGNING_SECRET=<independent random secret>
```

This secret must differ from `MVP_EDITOR_API_KEY` and must never be sent to the
browser. Therefore:

```text
editor credential != update signing authority
route present != gate activated
```

The preview route:

- requires the editor credential;
- requires `X-Pantheon-Human-Actor`;
- requires the server-side update signing authority;
- verifies exact project ownership and optimistic version;
- preserves the current Knowledge review status;
- calculates a unified Markdown diff;
- signs project, target, version, before/after digests, actor and expiry;
- persists nothing.

The apply route requires the same immutable effect, a valid signature, the exact
phrase `CONFIRMER UPDATE`, an idempotency key and the same declared human actor.
A new write is refused after expiration. An exact idempotent retry may still replay
the result already recorded by the owner transaction. The final write remains
owned by `knowledge.revise_knowledge`, including version increment, append-only
event and immutable replay.

The historical direct route is retired:

```text
PUT /v1/knowledge/{knowledge_id} -> 410 Gone
```

This closes the editor-key bypass. The mobile editor now keeps offline revisions
as local drafts and uses the same signed preview/confirmation path when online.
Legacy queued direct revisions are not auto-applied.

```text
UPDATE applied != Knowledge reviewed
Knowledge revised != Evidence
runtime success != proof
```

Identity assurance is currently **partial**: the declared actor is bound to the
shared editor credential. Individual SSO identity is not implemented and must not
be inferred from this gate.

The Questionnaire card remains session-local. It does not submit, persist or
apply any effect. Its answers may prefill Rapprochement only after an explicit
user action.

Not implemented in this lot:

- Situation persistence;
- owner-specific `CREATE`, `SUPERSEDE` or `CONFLICT` application;
- Document or Work Issue application from effect proposals;
- Knowledge review-status changes through this UPDATE gate;
- Decision and Gate projection;
- Rite Review cards;
- Agora;
- individually authenticated human identity / SSO;
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
Knowledge update module
motion
accessibility
```

HTML anatomy remains stable. The main renderer owns persisted-object cards;
`effects.js` owns proposal-only rapprochement and eligibility routing;
`knowledge_updates.js` owns only the signed Knowledge UPDATE interaction. Colors
and motion remain controlled by CSS variables and variants.

## Motion boundary

Motion is orientation-only:

- slow background gradient drift;
- one-shot recent-event sheen;
- restrained focus elevation;
- subtle human-attention pulse.

Motion never signifies approval, proof, successful execution or durable memory.
`prefers-reduced-motion` disables non-essential movement.
