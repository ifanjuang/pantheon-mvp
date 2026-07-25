# Cockpit V2 — structured agency interface foundation

Status: executable foundation implemented / spatial V2 route implemented candidate / PostgreSQL Agency Data API and Project persistence implemented candidate / live Agency Data Context Resolver implemented candidate / Notion collaborative sync contract partial / not adopted or production-authorized.

This branch implements the Cockpit V2 direction documented in Pantheon Next `PANTHEON_COCKPIT_STRUCTURED_AGENCY_INTERFACE.md` and `AGENCY_DATA_SYSTEM_OF_RECORD.md`.

## Product direction

The Cockpit is treated as a user-friendly interface over structured professional records shared between the agency and AI-assisted work.

```text
PostgreSQL Agency Data = default system of record for native agency records
Notion = optional collaborative projection for explicitly mapped fields
Pantheon governs consequential effects and status qualification
Hermes executes bounded operations
Cockpit exposes records and captures bounded intent
Human decides consequential effects when required
```

Notion is not required for normal Cockpit/Hermes operation.

## Implemented foundations

### Context Resolver

`mvp_vertical/cockpit/context_resolver.js` implements the federated resolver contract:

```text
_  Affaires
#  capabilities
@  people
*  global permitted search
```

The resolver normalizes accents/case, composes multiple providers, isolates provider failures, explains matches with `matched_field` / `match_reason`, deduplicates by stable identity where available and never imports provider-side selection state into the active Context.

Project matching now recognizes the PostgreSQL project code as an identity alias, so `_LIE` can resolve an Affaire whose display name is not itself code-prefixed.

`mvp_vertical/cockpit/v2_context.js` connects this contract to the live Agency Data HTTP surface. It adds a debounced UI with stale-response protection and explicit selection chips.

```text
search result != selected
selected != relied upon
relied upon != Evidence
scope_widened_implicitly = false
```

No result is selected automatically. An explicit user click adds a stable entity identity to the selected context projection.

### PostgreSQL Agency Data browser contract

`mvp_vertical/cockpit/agency_data_binding.js` is the browser-side owner-facing projection contract for native agency records.

Resources:

```text
projects
people
organizations
project_participations
```

The binding now accepts the actual HTTP response shapes and normalizes stable identities from:

```text
project_id
person_id
organization_id
participation_id
```

It:

- exposes `_`, `@` and `*` resolver projections through an injected bounded Agency Data transport;
- marks source authority as `agency_system_of_record` and `system_of_record=postgres`;
- preserves revision/source attribution;
- keeps database credentials out of the browser;
- provides `buildMutationIntent()` for a bounded Hermes/Agency Data mutation candidate with an expected revision;
- never marks that candidate as execution-authorized.

### PostgreSQL Agency Data persistence and API

The server-side candidate is partially implemented.

```text
mvp_vertical/sql/002_agency_data.sql
mvp_vertical/agency_data.py
mvp_vertical/agency_directory.py
mvp_vertical/agency_data_api.py
```

Implemented PostgreSQL structures:

```text
agency_projects
agency_people
agency_organizations
agency_project_participations
agency_project_events
```

`agency_project_events` is append-only and records actor identity, actor kind, expected/resulting revision, idempotency key, payload digest and result snapshot.

Implemented API routes:

```text
GET   /v1/agency/projects
GET   /v1/agency/projects/{project_id}
GET   /v1/agency/projects/{project_id}/participations
GET   /v1/agency/participations
GET   /v1/agency/people
GET   /v1/agency/people/{person_id}
GET   /v1/agency/organizations
GET   /v1/agency/organizations/{organization_id}
POST  /v1/agency/projects
PATCH /v1/agency/projects/{project_id}
```

People, Organization and Participation mutation policy is intentionally not exposed yet. Their current HTTP surface is read-only.

The read surface accepts bounded Cockpit/editor credentials and the Hermes execution credential. Project writes require an explicit `X-Pantheon-Actor` plus a recognized writer identity.

The API is not a generic SQL surface. Project updates use an explicit field allowlist, optimistic revision checks and idempotency. Responses retain:

```text
system_of_record = postgres
approval_inferred = false
```

### Hermes Agency Data ceiling

A Hermes API credential identifies the execution actor. It does not constitute Pantheon approval.

Until a verifiable Pantheon gate is wired server-side, the direct Hermes Project write ceiling is deliberately narrow:

```text
Hermes direct Project write admitted candidate:
  description

Hermes direct Project write blocked pending gate:
  project creation
  code
  display_name
  status
  phase
  location
  primary_client
  tags
```

Blocked consequential mutations raise `GovernanceGateRequired` and surface as HTTP `409` rather than being silently accepted.

Human/editor Project mutations remain bounded by the same field allowlist, actor trace, expected revision and idempotency controls.

```text
Hermes credential != approval
bounded write capability != unrestricted mutation authority
mutation persisted != professional validation
```

### Optional Notion collaboration contract

`mvp_vertical/cockpit/notion_agency_binding.js` does not register Notion as the primary owner/search source.

It models Notion as an optional collaborative projection over PostgreSQL-owned agency records.

Supported posture vocabulary:

```text
disabled
mirror_read_only
selective_bidirectional
```

A field policy declares:

```text
entity_type
field
notion_visible
notion_editable
sync_direction
conflict_policy
validation_rule
sensitivity
```

A Notion-originated edit becomes only a mutation candidate when:

1. the field is explicitly `notion_editable=true`;
2. its direction is `bidirectional`;
3. the Notion edit is based on the current PostgreSQL revision.

Otherwise it is rejected or classified as a conflict.

```text
Notion edit accepted as candidate != mutation executed
Notion editable != Notion authoritative
sync success != Evidence
```

The browser executes neither synchronization nor external writes.

Detailed contract: `docs/COCKPIT_V2_NOTION_AGENCY_BINDING.md`.

### Structured interface contract JS

`mvp_vertical/cockpit/structured_interface.js` establishes implementation-facing constants/helpers for:

```text
primary spaces: Pantheon / Décisions / Affaires / Connaissances / Outils
card roles: conversation / container / entity
card families: Pantheon, Decision, Project, Document, Evidence, Knowledge,
               Capability, RuntimeHost, RoleReference
Tag projection
Card Context Envelope
basic Card model validation
```

`Card Context Envelope` explicitly holds a root object, descendants, source refs, user additions and exclusions, with `scope_widened_implicitly=false`.

### Executable spatial V2 route

`mvp_vertical/cockpit/v2.html` is an executable candidate route that makes the product grammar visible without replacing the legacy Cockpit route.

The implementation is split into:

```text
spatial_navigation.js  pure navigation state / depth / sibling boundaries
v2_app.js               Card graph composition + Agency Data/project adapters
v2_context.js           live Context Resolver + explicit selected-context UI
styles/v2.css           universal Card skins, recto/verso, orbs and motion
styles/v2_context.css   Context Resolver presentation
v2.html                 five-space interaction surface
```

Implemented interaction grammar:

```text
root horizontal:
Pantheon ↔ Décisions ↔ Affaires ↔ Connaissances ↔ Outils

at deeper depth:
Left / Right = siblings in the current collection only
Up           = descend into declared children
Down         = return to parent
Space/button = front/back of the same object
```

Pointer swipes and explicit controls use the same navigation model. The breadcrumb exposes the current hierarchy and reduced-motion preferences disable spatial entrance animations.

Implemented visual projection rules include:

```text
Project       white front + restrained identity accent + thin accent back border
Document      family-color front + white family-border back
Knowledge     family-color front + white family-border back
Capability    gradient-capable active front + white bordered back
Containers    same anatomy with quieter emphasis
Status/Metric/Tag indicators share one bottom-right rail
```

A fixed Hermes dock is rendered against the current Card but its action remains deliberately disabled because the scoped Hermes handoff is not yet connected.

### Live Affaires and Intervenants hierarchy

The V2 route calls:

```text
GET /v1/agency/projects
```

and projects PostgreSQL records as sibling Project Cards under `Affaires`.

The user may load the Agency Data collection with the read key alone and navigate horizontally among real persisted Affaires. An optional project code/name/id loads deeper project projections.

For a selected PostgreSQL Project:

```text
Affaires
  ↓
Project
  ↓
Intervenants ↔ Documents ...
  ↓
ProjectParticipation
```

`Intervenants` is a container Card. Each ProjectParticipation remains an identifiable relation record carrying Person, Organization, role, type and revision projections; visual proximity does not merge those identities.

For the selected Project, established owner endpoints remain in use:

```text
/v1/projects/{project_id}/documents
/v1/projects/{project_id}/knowledge
/v1/projects/{project_id}/work-issues
```

This preserves the existing Document/Knowledge/Work Issue persistence instead of copying those records into Agency Data.

`Décisions` remains a cross-object projection from review-relevant Work Issues, Documents and Knowledge while preserving underlying identity.

## Current data flows

Implemented candidate read path:

```text
Cockpit V2 / Context Resolver / Hermes read
    ↓ bounded HTTP read
Agency Data API
    ↓
PostgreSQL Agency Data
```

Implemented candidate bounded Project write path:

```text
Human/editor or admitted Hermes adapter
    ↓ explicit API command + actor + expected revision + idempotency
Agency Data adapter
    ↓
PostgreSQL transaction + revision + append-only Project event
```

For consequential Hermes Project fields the current path intentionally stops before persistence:

```text
Hermes command
    ↓
GovernanceGateRequired
    ↓
no mutation
```

The missing component is the verifiable Pantheon gate handoff that can authorize an exact consequential Agency Data mutation without making Pantheon the executor.

With optional Notion collaboration, the target remains:

```text
                    PostgreSQL
                 system of record
                  ↑           ↓
       allowed Notion edit   projection
                  │           │
                  └── Notion ─┘
                 optional UI
```

The real synchronization mechanism remains unimplemented and external to the browser contracts.

## Conflict rule

No generic last-write-wins rule is accepted for business-significant fields.

Example:

```text
common base revision = 42
PostgreSQL/Hermes authorized mutation -> revision 43
Notion edit based on revision 42

result: conflict
not automatic overwrite
```

A field policy may select a bounded conflict posture such as `human_review`, `merge_append` or `postgres_authoritative`, but the frontend contract does not execute the resolution.

## Notion outage posture

When Notion is unavailable:

```text
PostgreSQL Agency Data  remains available
Cockpit                 remains available
Hermes/Agency Data      remains available within admitted authority
Notion collaboration    unavailable/degraded
```

PostgreSQL remains the system of record. Recovery compares revisions before resuming synchronization; Notion unavailability does not transfer ownership or block native Agency Data writes.

## Implementation status

```text
Universal Card front/back anatomy                         implemented candidate
Tag/Status/Metric indicator rail                         implemented candidate
Spatial navigation state + keyboard/pointer gestures     implemented candidate
Five-space V2 route                                      implemented candidate
PostgreSQL Agency Project schema                         implemented candidate
People/Organization/ProjectParticipation schema          implemented candidate
Global Affaires read API                                 implemented candidate
People/Organization/Participation read APIs              implemented candidate
Global Affaires sibling Cards in V2                      implemented candidate
Project → Intervenants → Participation hierarchy         implemented candidate
Agency Project revision/idempotency/event adapter        implemented candidate
Human/editor bounded Project writes                      implemented candidate
Hermes Agency Data reads                                 implemented candidate
Hermes reversible direct Project description write       implemented candidate
Hermes consequential Project mutation                    blocked pending verifiable gate
People/Organization/Participation writes                 not implemented
Context Resolver federated provider contract             implemented candidate
Context Resolver live Agency Data HTTP transport         implemented candidate
Context Resolver explicit selected-context UI            implemented candidate
Cross-object Décisions projection                        implemented candidate
Fixed Hermes dock presentation                           implemented candidate
Scoped Hermes dock handoff                               not wired
Notion field sync policy contract                        implemented candidate
Live Notion synchronization adapter                      not implemented
Production adoption                                      not authorized
```

## Next slices

```text
1 add standalone Person / Organization Card navigation where useful
2 connect scoped Hermes dock handoff to Card Context Envelope + selected Context
3 add verifiable Pantheon gate receipt for consequential Agency Data mutations
4 define bounded Person / Organization / Participation mutation policies
5 Tag Registry owner API + picker
6 external Notion sync adapter for declared field policies
7 richer Document revision/representation/issues Cards
8 Knowledge family hierarchy
9 Outils live Capability/RuntimeHost/model observations
```

## Boundaries

```text
card != source of truth
search result != selected context
selected context != Evidence
PostgreSQL Agency Data record != Pantheon governance Decision
PostgreSQL system of record != Pantheon governance authority
Hermes credential != approval
Notion projection != system of record
Notion editable != unrestricted write authority
sync candidate != executed mutation
revision conflict != last-write-wins
Document != Evidence
Document != Knowledge
role reference != runtime agent
host observed != healthy/safe
model discovered != task-authorized
```

The legacy Cockpit remains available while `v2.html` is introduced as a separate executable candidate route. No live Notion synchronization, scoped Hermes dock handoff, People/Organization/Participation write policy, production credential configuration or production activation is claimed by this PR.
