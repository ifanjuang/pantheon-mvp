# Cockpit folder and card information matrix

Status: UX/data contract. A displayed field is not automatically a source of truth, Evidence, approval or production authorization.

| Object | Recto | Verso / detail | Actions | Current status |
|---|---|---|---|---|
| Pantheon Context | active Affaire; Document count; Knowledge count; Work reviews; attention count | conversation/runtime binding limits; context boundaries; non-equivalences | open Affaire; clarify request; open Décisions | implemented projection |
| Project Card | project id/name; Document count; Knowledge count; open Work count; human-review signal; observed documentary phases | target Project Profile: type; address/commune; lifecycle phase; mission; client; typed surfaces; parcels; PLU/PLUi; constraints; source/date/review/freshness | Documents; Travail; Knowledge liée; Décisions | implemented; Project Profile data partial |
| Phase folder | phase code; label; Document count | Affaire; logical-folder boundary; first Document names | open filtered phase | implemented |
| Intervenants & contacts | directory purpose; contact/client/BET counts when available | person; organization; project role; mission; email; phone; active period; participation status; source; last verification | consult; add/edit only after owner API | UX implemented; data API absent |
| Entreprises | lots; selected companies; contracts; insurance alerts when available | stable company identity; project engagement; lot; consultation; quote; selection; contract; insurance; works; reservations; source; verification | consult; add/edit only after owner API | UX implemented; data API absent |
| Project Document | title/object; document type; phase; index; analysis status; observed format | source identity; exact version/digest when available; extraction; composition; provenance; limitations | detail; resource preview; governed downstream actions where already supported | implemented existing vertical |
| Knowledge folder | family; item count | logical-container boundary; item list; source-ownership warning | open; create/move/add-source after persistence binding | local projection implemented |
| Knowledge Item | title; family; version; review status; source/site signals | provenance; Markdown/content; linked sources; linked sites; review/freshness; limitations | inspect; signed update; eligible proposal-only resource actions | implemented existing vertical; Knowledge write chokepoint can be injected on current main |
| Work Issue | title; type; priority; status | description; case/scope; Task Contract; requested effect; comments; Hermes runs; append-only events | inspect/review existing behavior | implemented existing vertical |
| Decision Request / Gate | validation type; Affaire; Work Issue; priority; candidate summary | question/result; requested effect; Task Contract; Gate != Decision warning | open Work Issue; persisted Decision disabled until owner endpoint | implemented projection; Decision API absent |
| Capability lifecycle | supported capability types; manager status; Hermes executor status; live-record availability | capability id/type; installation; enablement; activation scope; health; update; source; native executor boundary; rollback/risk when owner data exists | read posture now; propose/install/enable/update/suspend/retire only after Cockpit API + Pantheon gate + human Decision | manager + Hermes executor implemented; Cockpit API/runtime connection absent |
| Document Runtime observations | candidate stack status | per source: observation source; observed_at; Paperless/gateway; Pantheon PDP; Docling; Hermes native inventory; synthetic acceptance; no global health | read-only when adopted | #59/#61/#62 candidate branches, not current live main state |
| PDP / PEP | implementation/readiness observations when available | HttpPolicyClient boundary; PDP source/meta; effect authorization distinction | read-only | client implemented; live target not established by repo |
| Clarification questionnaire | expected output; priorities; external-action intent | local answers; generated summary | save local draft; prepare summary; proposal-only rapprochement | implemented local-only |

## Project phase folders

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

These folders are Cockpit navigation projections. They do not rename, move, delete or change permissions on NAS/Paperless sources.

## Capability responsibility split

```text
Pantheon: governance, scope, status qualification, gates, activation decision, trace.
Hermes: bounded native execution after authorization.
OpenWebUI/Cockpit: display, navigation, bounded intent capture.
Human: consequential approval/decision.
Forbidden: self-approval, silent install/update/activation, safety inference from health, receipt-to-Evidence promotion.
```
