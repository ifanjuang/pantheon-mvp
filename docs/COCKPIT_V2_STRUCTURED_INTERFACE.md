# Cockpit V2 — structured agency interface foundation

Status: executable foundation implemented / spatial V2 route implemented candidate / PostgreSQL Agency Data seam implemented / Notion collaborative sync contract partial / not adopted or production-authorized.

This branch begins the Cockpit V2 implementation direction documented in Pantheon Next `PANTHEON_COCKPIT_STRUCTURED_AGENCY_INTERFACE.md`.

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

### Context Resolver JS

`mvp_vertical/cockpit/context_resolver.js` implements an extensible client-side resolver contract:

```text
_  Affaires
#  capabilities
@  people
*  global permitted search
```

The resolver normalizes accents/case, composes multiple providers, isolates provider failures, explains matches with `matched_field` / `match_reason`, deduplicates by stable identity where available and never imports provider-side selection state into the active Context.

### PostgreSQL Agency Data owner seam

`mvp_vertical/cockpit/agency_data_binding.js` is now the default owner-facing projection seam for native agency records.

Conceptual resources:

```text
projects
people
organizations
project_participations
```

The module:

- exposes `_`, `@` and `*` resolver projections through an injected bounded Agency Data transport;
- marks source authority as `agency_system_of_record` and `system_of_record=postgres`;
- keeps database credentials out of the browser;
- provides `buildMutationIntent()` for a bounded Hermes/Agency Data mutation candidate with an expected revision;
- never marks that candidate as execution-authorized.

This does not implement a PostgreSQL migration, direct SQL access or a Hermes server-side write adapter.

### Optional Notion collaboration contract

`mvp_vertical/cockpit/notion_agency_binding.js` no longer registers Notion as the primary owner/search source.

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

`mvp_vertical/cockpit/v2.html` is now an executable candidate route that makes the product grammar visible without replacing the legacy Cockpit route yet.

The implementation is split into:

```text
spatial_navigation.js  pure navigation state / depth / sibling boundaries
v2_app.js               Card graph composition and existing project endpoint adapter
styles/v2.css           universal Card skins, recto/verso, orbs and motion
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

A fixed Hermes dock is rendered against the current Card but its action remains deliberately disabled in this tranche because the scoped Hermes handoff is not yet connected.

The V2 route currently reuses the existing per-project endpoints for Documents, Knowledge and Work Issues. It therefore exposes one explicitly loaded Project at a time; it does not claim the future global PostgreSQL Agency Data project listing is live.

`Décisions` is already projected cross-object from review-relevant Work Issues, Documents and Knowledge while preserving the underlying entity identity/family.

## Target data flow

Normal operation:

```text
Cockpit / Hermes
       ↓
bounded Agency Data API
       ↓
PostgreSQL
system of record
```

With optional Notion collaboration:

```text
                    PostgreSQL
                 system of record
                  ↑           ↓
       allowed Notion edit   projection
                  │           │
                  └── Notion ─┘
                 optional UI
```

The real synchronization mechanism remains external to these browser contracts.

## Conflict rule

No generic last-write-wins rule is accepted for business-significant fields.

Example:

```text
common base revision = 42
PostgreSQL/Hermes -> phase EXE, revision 43
Notion edit based on revision 42 -> phase ACT

result: conflict
not automatic overwrite
```

A field policy may select a bounded conflict posture such as `human_review`, `merge_append` or `postgres_authoritative`, but the frontend contract does not execute the resolution.

## Notion outage posture

When Notion is unavailable:

```text
PostgreSQL Agency Data  remains available
Cockpit                 remains available
Hermes/Agency Data      remains available
Notion collaboration    unavailable/degraded
```

PostgreSQL remains the system of record. Recovery compares revisions before resuming synchronization; Notion unavailability does not transfer ownership or block native Agency Data writes.

## Planned next slices

```text
implemented candidate
  universal Card front/back anatomy
  standardized Tag/Status/Metric indicator rail
  spatial navigation state + keyboard/pointer gestures
  five-space V2 route
  first cross-object Décisions projection
  fixed Hermes dock presentation

next
  Context Resolver interaction inside Pantheon dialogue
  live bounded Agency Data API transport over PostgreSQL
  all-project Affaires collection from Agency Data
  real Project / Person / Organization / Participation projections
  Hermes server-side Agency Data mutation adapter with revision checks
  external Notion sync adapter for declared field policies
  Tag Registry owner API + picker
  Document revision/representation/issues Cards
  Knowledge family hierarchy
  Outils live Capability/RuntimeHost/model observations
  scoped Hermes dock handoff + attached answer projections
```

## Boundaries

```text
card != source of truth
search result != selected context
PostgreSQL Agency Data record != Pantheon governance Decision
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

The existing visible Cockpit remains available while `v2.html` is introduced as a separate executable candidate route. No database migration, live Notion synchronization service, credential configuration, global Agency Data listing, Hermes handoff or production activation is claimed by this PR.
