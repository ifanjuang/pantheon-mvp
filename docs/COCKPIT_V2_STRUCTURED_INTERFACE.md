# Cockpit V2 — structured agency interface foundation

Status: executable foundation implemented / product UI migration partial / not adopted or production-authorized.

This branch begins the Cockpit V2 implementation direction documented in Pantheon Next `PANTHEON_COCKPIT_STRUCTURED_AGENCY_INTERFACE.md`.

## Product direction

The Cockpit is treated as a user-friendly interface over structured professional records shared between the agency and AI-assisted work.

```text
Pantheon governs.
Hermes executes bounded operations.
Cockpit exposes and captures bounded intent.
Owner systems remain authoritative for their data/runtime.
Human decides consequential effects.
```

## Implemented in this first slice

### Context Resolver JS

`mvp_vertical/cockpit/context_resolver.js` implements an extensible client-side resolver contract:

```text
_  Affaires
#  capabilities
@  people
*  global permitted search
```

The resolver:

- normalizes accents/case;
- supports prefix-weighted project search;
- searches normalized labels, descriptions, aliases, tags and provider-supplied search terms;
- accepts injected providers rather than embedding fake data or becoming a database;
- deduplicates global results by stable identity;
- returns normalized entity projections;
- never auto-selects a search result into context.

Provider binding to real owner APIs remains to implement.

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

This is a frontend contract only. It does not establish an authorization service, retrieval engine, database schema or Hermes runtime.

## Planned next slices

```text
1 universal Card primitive and front/back anatomy
2 standardized tag/status/metric orbs
3 spatial navigation engine
4 Context Resolver UI in Pantheon dialogue
5 Tag Registry owner API + picker
6 Project Card and ProjectFact bindings
7 Document revision/representation/issues cards
8 Décisions cross-object attention projection
9 Knowledge families/items
10 Outils hierarchy + RuntimeHost/model observations + role references
11 fixed scoped Hermes dock + attached answer projections
```

## Data direction

The implementation should bind progressively to owner records such as:

```text
Project
Person / Organization / Participation
ProjectFact
Document / Revision / Representation / Issue
Evidence
Knowledge
Tag / TagAssignment
WorkIssue
DecisionRequest / Decision
CapabilityRecord
RuntimeHostObservation / RuntimeModelObservation
CardComment
```

No database migration is introduced by this slice.

## Boundaries

```text
card != source of truth
tag != established fact
search result != selected context
Document != Evidence
Document != Knowledge
Decision projection != Decision record
role reference != runtime agent
host observed != healthy/safe
model discovered != task-authorized
```

The existing Cockpit UI remains in place while these foundations are introduced; this PR starts the migration rather than claiming the spatial V2 UI is already complete.