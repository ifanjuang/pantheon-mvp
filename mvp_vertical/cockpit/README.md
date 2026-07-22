# Cards-first Cockpit Candidate

Status: implemented external UI and bounded write candidate — not adopted, not activated, not production-authorized.

This directory contains the first cards-first cockpit shell served at `/cockpit/`.
It composes the existing bounded Document, Knowledge and Work Issue projections.
It does not add a card database, approval engine, workflow engine, runtime,
provider router, crawler, vectorization service, external action path or memory
promotion path.

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

The visual projection is derived from independent inputs:

```text
object kind
+ current owner-defined status
+ recent event where the underlying projection exposes one
+ optional observed resource profile
```

A card is not the underlying object and never owns its status.

## Current implemented families

- Project Document cards from `GET /v1/projects/{parent_project_id}/documents`.
- Knowledge cards from `GET /v1/projects/{parent_project_id}/knowledge`.
- Work Issue cards from `GET /v1/projects/{parent_project_id}/work-issues`.
- Read-only Resource Profiles from `GET /v1/projects/{parent_project_id}/resource-profiles`.
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

## File format and observed composition

Document cards may show a compact format badge and resource indicators without
changing their base anatomy. The read-only profile derives, where available:

```text
extension
media type
format family
text observed
images observed
tables observed
composition candidate
```

Format families currently include:

```text
PDF
image
text
word-processing document
spreadsheet
presentation
archive
other
```

Composition candidates currently include:

```text
text only
structured text / tables
text and images
image with extracted text
images only
unknown
```

The profile is calculated from the current extraction JSON and derived Markdown.
It is explicitly non-exhaustive. Therefore:

```text
image indicator != complete visual inspection
text extracted != source verified
format recognized != content approved
```

No new document status or authority is inferred from these indicators.

## Knowledge-linked site addresses

A Knowledge card may expose several web addresses already present in its Markdown.
The profile deduplicates addresses and may classify common hosts for orientation,
including legal references, safety references, geodata, public data, official
public sites and general web sources.

The current retrieval profile is always:

```text
mode: address_only
crawl_status: not_authorized
vector_status: not_indexed
structure_indexed: false
```

The cockpit performs no URL request while loading or displaying a card. A link is
not a fetched source, an indexed source or Evidence.

Possible future coverage modes are documented but not implemented:

```text
address_only
structure_only
selected_pages
full_content
```

The intended responsibility split is:

```text
Pantheon governs host/path scope, coverage mode, activation, update and rollback.
Hermes may execute an explicitly authorized crawl or indexing handoff.
The cockpit and OpenWebUI display addresses, coverage and health.
The human approves consequential scope and activation.
```

Forbidden by this candidate:

- following undeclared links;
- default full-site crawling;
- hidden authentication or session reuse;
- treating sitemap discovery or runtime success as approval;
- treating a vector index as Evidence or canonical Knowledge;
- silently widening from structure-only to content indexing;
- automatically refreshing or deleting indexed content without a governed update
  and rollback path.

A future `structure_only` binding should index only a reviewed site map or bounded
navigation graph — for example canonical URLs, titles, headings and parent/child
relations — so retrieval can locate candidate pages before any separately scoped
content fetch.

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
- ignores terminal whitespace-only differences when deciding whether a change is
  material, while preserving the exact confirmed Markdown for a material write;
- signs project, target, version, exact before/after digests, actor and expiry;
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
- web crawling or web-content vectorization;
- persisted per-site crawl policies, manifests, refresh schedules or rollback;
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
resource indicators
variants
effect preview module
Knowledge update module
motion
accessibility
```

HTML anatomy remains stable. The main renderer owns persisted-object cards;
`resources.js` enriches those projections with read-only format/composition and
linked-site indicators; `effects.js` owns proposal-only rapprochement and
eligibility routing; `knowledge_updates.js` owns only the signed Knowledge
`UPDATE` interaction. Colors and motion remain controlled by CSS variables and
variants.

## Motion boundary

Motion is orientation-only:

- slow background gradient drift;
- one-shot recent-event sheen;
- restrained focus elevation;
- subtle human-attention pulse.

Motion never signifies approval, proof, successful execution or durable memory.
`prefers-reduced-motion` disables non-essential movement.
