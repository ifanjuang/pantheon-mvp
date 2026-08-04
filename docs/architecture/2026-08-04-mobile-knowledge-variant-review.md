# Mobile Knowledge proposal variant review

Date: 2026-08-04
Status: implemented candidate in this repository; live Hermes and real-device acceptance not established.

## Objective

Extend the existing mobile Markdown editor so one exact selection can receive one or two immutable Hermes proposal variants. A human may compare, select, reject and explicitly apply one variant without confusing selection with authorization or proposal with Evidence.

## Existing owners reused

```text
Knowledge source and version          knowledge_items
bounded intelligent-edit request      knowledge_edit_requests
proposal alternatives                 knowledge_edit_variants
human/Hermes review trace             knowledge_edit_review_events
Knowledge application                 knowledge.apply_edit_request
mobile draft and offline request queue existing PWA
```

The proposal request remains one scope:

```text
knowledge_id
base_version
selection_start / selection_end
selected_text_snapshot
selected_text_digest
instruction
requested_variant_count = 1 or 2
```

Variants are child candidates of that request. They do not widen the scope and do not become independent tasks.

## Lifecycle

```text
mobile request queued
-> Hermes submits A, and B when requested
-> request becomes proposed only when the required count exists
-> human selects one variant
-> optional human rejection, or explicit apply
-> current Knowledge version and selection digest are rechecked
-> selected replacement is applied through the existing Knowledge revision path
```

```text
variant proposed != selected
variant selected != edit applied
edit applied != Knowledge reviewed
Knowledge revised != Evidence
```

## API split

Editor-key routes:

```text
POST /knowledge/{knowledge_id}/variant-edit-requests
GET  /knowledge/{knowledge_id}/edit-reviews
GET  /edit-requests/{request_id}/review
POST /edit-requests/{request_id}/select-variant
POST /edit-requests/{request_id}/reject
POST /edit-requests/{request_id}/apply-selected
```

Hermes-key route:

```text
PUT /edit-requests/{request_id}/variants/{variant_label}
```

Hermes can submit proposals but cannot select, reject or apply them. Editor credentials cannot submit a Hermes variant. Human review routes additionally require `X-Pantheon-Human-Actor`.

## Persistence

`knowledge_edit_variants` stores immutable proposal content and digest per A/B label. `knowledge_edit_review_events` is append-only and records proposal submission, human selection, rejection and selected-variant application.

The current request row stores the selected variant reference only to support projection and application. The event remains the historical trace.

## Mobile behavior

The existing editor remains the primary surface. A separate `variant_review.js` adapter:

- redirects future selection actions through the scoped variant request route;
- keeps a dedicated device-local queue under the existing clearable Knowledge prefix;
- adds an explicit A/B action;
- loads proposals only for the open Knowledge item;
- displays the source selection and one unified diff per variant;
- exposes explicit refresh rather than a hidden polling loop;
- separates select, reject and apply actions;
- refreshes the local Knowledge snapshot after successful application.

The service worker caches the new shell file but excludes all authenticated API roots.

## Non-authority flags

The routes preserve explicit facts such as:

```text
knowledge_mutated = false       # request, proposal, selection, rejection
execution_authorized = false    # request
human_selection_required = true # Hermes proposal
edit_applied = false            # selection
review_status_promoted = false  # application
evidence_admitted = false       # every route
```

## Verification

The slice covers:

- two variants sharing one immutable selection scope;
- proposal completion only after the required variant count;
- proposal and selection idempotence;
- selection without Knowledge mutation;
- rejection without Knowledge mutation;
- selected-variant application through the existing optimistic revision path;
- append-only review events;
- separate editor and Hermes keys;
- human actor requirement;
- PWA shell caching and API cache exclusion;
- explicit refresh with no polling loop;
- mobile one-column comparison and keyboard focus visibility;
- JavaScript syntax.

## Remaining issue #165 scope

```text
structured request-revision annotations on mobile Knowledge proposals
whole-document coherence report candidate
related summary/introduction/TOC/conclusion adaptation candidates
conflict-safe offline replay for review decisions, not only request creation
real-device accessibility and offline recovery acceptance
```

Those slices must reuse this request/variant/revision boundary rather than add a general workflow engine.
