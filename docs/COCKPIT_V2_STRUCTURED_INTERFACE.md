# Cockpit V2 — structured agency interface foundation

Status: executable foundation implemented / product UI migration partial / PostgreSQL Agency Data seam implemented / Notion collaborative sync contract partial / not adopted or production-authorized.

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
1 universal Card primitive and front/back anatomy
2 standardized tag/status/metric orbs
3 spatial navigation engine
4 Context Resolver UI in Pantheon dialogue
5 live bounded Agency Data API transport over PostgreSQL
6 Hermes server-side Agency Data mutation adapter with revision checks
7 external Notion sync adapter for declared field policies
8 Tag Registry owner API + picker
9 Project Card / Person / Organization / Participation real projections
10 Document revision/representation/issues cards
11 Décisions cross-object attention projection
12 Knowledge families/items
13 Outils hierarchy + RuntimeHost/model observations + role references
14 fixed scoped Hermes dock + attached answer projections
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

The existing visible Cockpit remains in place while these foundations are introduced. No database migration, live Notion synchronization service, credential configuration or production activation is claimed by this PR.
