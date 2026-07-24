# Cockpit V2 — optional Notion agency-data binding

Status: executable projection seam implemented / live connector transport not connected / read-only only.

This note documents the first optional Notion integration seam for the Cockpit V2.

The design is intentionally asymmetric:

```text
Notion owner records
      ↓
external bounded connector transport
      ↓ normalized read-only projections
notion_agency_binding.js
      ↓
Context Resolver / future Card renderers
```

The browser never receives Notion credentials and this slice does not call the Notion API directly.

```text
connected != adopted as owner
read permission != write authorization
workspace reachable != data trustworthy
Notion record != Pantheon governance record
```

## Pilot owner mapping

The current IFJA workspace already contains business structures that map closely to Cockpit V2 owner concepts:

| Notion data source | Cockpit projection | Initial posture |
|---|---|---|
| `_Affaires` | Project / Affaire | optional read-only owner projection |
| `_Personnes` | Person | optional read-only owner projection |
| `_Sociétés` | Organization | optional read-only owner projection |
| `_Intervenants` | ProjectParticipation / CompanyEngagement projection | optional read-only owner projection |
| `_Décisions` | agency decision/reference record | not yet wired; must remain distinct from Pantheon governance Decision |

The runtime code deliberately refers to collection names, not workspace-specific IDs or credentials.

## Field ownership principle

Notion is not a generic mirror of the whole Cockpit.

Examples of fields that may legitimately remain Notion-owned when the binding is adopted:

```text
Project.code
Project.status
Project.phase
Project.location
project administrative dates
project surface fields
Person identity/contact data
Organization identity/contact data
ProjectParticipation relations
```

Examples that must not become Notion-owned merely because a Notion property exists:

```text
Pantheon Evidence status
Pantheon governance Decision
capability approval/activation
Hermes run authority
runtime health/safety qualification
canonical Tag vocabulary
```

## Context Resolver integration

`mvp_vertical/cockpit/notion_agency_binding.js` registers optional providers for:

```text
_  -> _Affaires
@  -> _Personnes
*  -> _Sociétés + _Intervenants, plus the normal resolver federation
```

The resolver itself now accepts multiple providers per namespace, so a Notion source does not silently replace another Project, People or global-search source.

Search results retain source attribution:

```text
source.system = notion
source.collection = _Affaires | _Personnes | _Sociétés | _Intervenants
source.external_id
source.url
source.authority = external_owner_projection
```

A result remains unselected until the active Context explicitly admits it.

## Transport contract

The binding requires an injected transport when mode is `read_only`.

The transport receives only a bounded request shape:

```text
operation: search
effect: read_only
provider: notion
collection
query
limit
currentScope
```

It returns either a list or `{ results: [...] }` of records carrying stable external identity, source URL and field values.

The concrete live transport remains intentionally unimplemented in this PR. A future binding may use the reviewed external connector capability path (for example Hermes + a bounded connector gateway) but that is a separate adoption/installation/credential decision.

## Modes

```text
disabled
read_only
```

There is no write mode in this slice.

A future write-back mode must be field-owner aware and route consequential external effects through Pantheon preflight + an applicable human Decision before Hermes/external connector execution.

No `sync_everything` mode is planned.

## Notion decisions boundary

The existing agency `_Décisions` data source is useful as a professional project/agency decision record, but it must not be collapsed into Pantheon's governance Decision.

```text
AgencyDecisionRecord (Notion)
!=
PantheonGovernanceDecision
```

The two may be related when useful, for example an agency/client choice may support or contextualize a later Pantheon gate. One does not automatically authorize the other.

## Tags boundary

Notion multi-selects are not the canonical Tag Registry by default.

The Cockpit Tag object carries richer identity and vocabulary control:

```text
tag_id
name
description
icon_key
color
aliases
status/provenance
```

A Notion property may project/display tags, but arbitrary Notion text or multi-select creation must not silently create canonical tags.

## Current implementation status

```text
Context Resolver multi-provider composition       implemented
Notion agency projection normalizers             implemented
Notion optional binding mode disabled/read_only  implemented
Notion resolver provider registration            implemented
source attribution                               implemented
browser Notion credential handling               forbidden / absent
live Notion transport                             not connected
Notion write-back                                not implemented
Notion _Décisions projection                     not wired
production adoption                              not decided
```
