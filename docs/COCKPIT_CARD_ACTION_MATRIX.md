# Cockpit five-space information architecture and card contract

Status: implemented external UI support — partial data bindings; not adopted, not activated, not production-authorized.

This document records the executable Cockpit projection added on top of the existing cards-first vertical. It follows the Pantheon Next five-space information architecture without making the Cockpit a runtime, approval engine, source of truth, memory engine or capability installer.

```text
Pantheon Next governs.
Hermes executes bounded handoffs.
The Cockpit exposes and captures bounded intent.
The human decides consequential effects.
```

## Primary navigation

```text
Pantheon
Affaires
Connaissances
Outils
Décisions
```

`Documents`, `Travail`, `Questionnaire`, Resource Profiles and proposal-only effects remain bounded projections or actions inside those spaces. They are no longer the primary professional navigation.

## Card and folder contract

| Type | Recto | Verso / detail | Implemented actions | Binding status |
|---|---|---|---|---|
| Pantheon Context | active Affaire, counts of Documents / Knowledge / review items, attention signal | explicit context limits, missing conversation/runtime bindings, non-equivalences | open Affaire, open local clarification questionnaire, open Décisions | implemented projection; conversation runtime not connected |
| Project Card / Affaire | project id, document / Knowledge / open-work counts, human-review signal | observed documentary phases plus explicit missing Project Profile fields | documents, work, linked Knowledge, decisions | implemented projection; full Project Profile not exposed |
| Project phase folder | phase code/title and document count | project identity, logical-folder boundary, first documents in the phase | open filtered phase view | implemented from existing Document naming metadata |
| Intervenants & contacts | directory purpose and partial state | expected person / organization / project-role fields and categories | consult contract; mutation disabled | UX implemented; business directory endpoint not connected |
| Entreprises | directory purpose and partial state | expected company identity, lot, consultation, contract, insurance, works and reservation fields | consult contract; mutation disabled | UX implemented; company engagement endpoint not connected |
| Project Document Card | title, type/phase/index, extraction status and observed format | source identity, digest, extraction, format/composition, provenance and limitations | existing detail actions and resource previews | implemented existing vertical |
| Knowledge folder | family title and item count | logical-container boundary and listed items | open local folder view; create/add-source disabled | navigation projection implemented; folder persistence not connected |
| Knowledge Item | title, family, version, review status, source/site signals | provenance, review state, linked sites, resource/navigation previews | existing signed Knowledge update and proposal-only resource actions where eligible | implemented existing vertical |
| Work Issue | title, type, priority, current state | scope, Task Contract, comments, Hermes runs, append-only events | existing review/detail behavior | implemented existing vertical |
| Decision Request / Gate | validation type, linked Work Issue, priority, candidate summary | requested effect, Task Contract, explicit distinction Gate != Decision | open Work Issue; Decision-record write disabled | derived from Work Issues in `review`; separate Decision endpoint not exposed |
| Outils / capability catalogue | supported capability families and partial runtime posture | installation, enablement, scope activation, health, update and rollback axes | inventory/install/enable/update controls disabled until API binding exists | backend lifecycle manager implemented; Cockpit inventory API not connected |
| PDP / PEP status card | repository implementation posture | HttpPolicyClient and capability-manager boundary | read-only | repo implementation known; target deployment/health not observed |
| Clarification questionnaire | expected output / priorities / external-action intent | session-local answers and summary | save local draft, prepare summary, feed proposal-only rapprochement flow | implemented local-only |

## Project Card information density

The executable card only displays values actually exposed by the current MVP APIs. It does not invent missing project data.

Target recto fields when the Project Profile binding is added:

```text
project display name
project code
project type
commune / locality
current project phase
project lifecycle status
mission-scope summary
primary client display name when permitted
one explicitly typed principal surface
material warning / review badge
```

Target verso fields:

```text
administrative identity
address and locality
client and primary contacts
parcel references
explicitly typed surfaces
PLU / PLUi document and zone claims
applicable-regulation candidates
project constraints and key facts
source / date / review / freshness for material fields
```

The current MVP intentionally shows `non exposé par ce vertical` for data that is not available rather than generating a plausible value.

## Folder behavior

### Project phase folders

```text
00_Gestion
10_Conception
20_Autorisations
30_DCE
40_Marche
50_Chantier
60_Reception
90_Sinistres
```

They are logical Cockpit navigation over project Documents. Opening one filters the already-loaded Document projections. It does not rename, move or delete a NAS source.

### Knowledge folders

The current executable slice groups loaded Knowledge by its existing `family` and lets the user open that collection locally.

```text
folder membership != source ownership
Cockpit folder != physical directory
open folder != change permissions
```

Nested-folder persistence, create/move/delete and intake actions remain disabled until a dedicated owner API exists.

## Decision inbox boundary

The current Work Issue vertical has no separate persisted Decision endpoint. Therefore the `Décisions` space only exposes a truthful `Decision Request / Gate` projection for Work Issues in human review.

```text
Decision Request / Gate != Decision
review requested != approval
Decision recorded != action executed
```

The UI disables `Enregistrer une Decision` instead of creating a parallel Decision store.

## Outils boundary

`mvp_vertical.capability_manager` already implements the bounded lifecycle seam for:

```text
skill
function
workflow
runtime_agent
plugin
mcp_binding
connector
```

The five-space Cockpit exposes that capability-management posture but does not fabricate a live inventory. Mutation actions remain disabled until an owner API provides current CapabilityRecords and routes consequential operations through the existing policy chokepoint and native executor.

```text
installed != approved
enabled != activated for a scope
healthy != safe
update_available != update_authorized
technical receipt != Evidence
```

## Implementation boundary

Implemented by this slice:

- five-space primary navigation;
- Project Card projection;
- project phase folder cards and filtered phase navigation;
- Contacts and Entreprises directory contracts with explicit partial state;
- Knowledge family folders and local filtered navigation;
- Decision Request inbox derived from review-state Work Issues;
- Outils lifecycle posture cards;
- explicit per-card actions, with unavailable mutations visibly disabled;
- responsive card-frame grammar for project, folder, Knowledge-folder, directory, Decision and tool projections.

Not implemented by this slice:

- project master/profile persistence;
- participant or company databases;
- nested Knowledge folder persistence;
- general multi-project Affaires listing endpoint;
- separate Decision persistence endpoint;
- live capability inventory endpoint;
- capability mutation UI/API binding;
- Hermes conversation runtime inside the Cockpit;
- installation, activation, deployment or production authorization.
