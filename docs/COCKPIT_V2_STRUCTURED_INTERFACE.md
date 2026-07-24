# Cockpit V2 — structured agency interface foundation

Status: executable foundation implemented / product UI migration partial / optional Notion projection seam implemented / not adopted or production-authorized.

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
- accepts multiple injected providers per namespace rather than embedding fake data or becoming a database;
- isolates provider failures and returns provider-error observations without collapsing the whole search;
- deduplicates global results by stable identity where available;
- explains matches with `matched_field` / `match_reason`;
- returns normalized entity projections;
- never imports provider-side `selected` state into search results.

Live owner API bindings remain separate from the resolver.

### Optional Notion agency binding seam

`mvp_vertical/cockpit/notion_agency_binding.js` adds the first optional read-only agency-data binding contract.

Initial pilot mapping:

```text
_Affaires      -> Project / Affaire
_Personnes     -> Person
_Sociétés      -> Organization
_Intervenants  -> ProjectParticipation projection
```

The module registers Notion-backed providers with the Context Resolver when explicitly created in `read_only` mode.

```text
_  uses Notion Affaires when attached
@  uses Notion People when attached
*  can additionally discover organizations and participations
```

The binding never handles Notion credentials in the browser. It requires an injected bounded transport and sends only a `read_only` search request contract. The concrete live connector transport is not connected in this PR.

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

This is a frontend contract only. It does not establish an authorization service, retrieval engine, database schema or Hermes runtime.

## Planned next slices

```text
1 universal Card primitive and front/back anatomy
2 standardized tag/status/metric orbs
3 spatial navigation engine
4 Context Resolver UI in Pantheon dialogue
5 live optional Agency Data transport binding (Notion pilot read-only)
6 Tag Registry owner API + picker
7 Project Card / Person / Organization / Participation real projections
8 Document revision/representation/issues cards
9 Décisions cross-object attention projection
10 Knowledge families/items
11 Outils hierarchy + RuntimeHost/model observations + role references
12 fixed scoped Hermes dock + attached answer projections
```

The live Notion connector must remain optional. Cockpit V2 must still work with another Agency Data binding or no Notion binding at all.

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

A physical database choice does not collapse authority. Where Notion remains the declared owner of a Project/Person field, a normalized Cockpit/PostgreSQL projection is not automatically a replacement owner.

No database migration is introduced by this slice.

## Boundaries

```text
card != source of truth
tag != established fact
search result != selected context
Notion record != Pantheon governance record
read permission != write authorization
Document != Evidence
Document != Knowledge
Decision projection != Decision record
role reference != runtime agent
host observed != healthy/safe
model discovered != task-authorized
```

The existing Cockpit UI remains in place while these foundations are introduced; this PR starts the migration rather than claiming the spatial V2 UI is already complete.