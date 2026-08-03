# Cockpit D3 knowledge map — planning spec

Status: planning specification — documented, non-implemented in `pantheon-mvp`.
Boundary profile: candidate design note. It defines a visual/analytical contract
only. It does not implement a renderer, a layout engine, a data endpoint, a
retrieval path, Evidence admission, memory promotion or any runtime.

This document specialises the Cockpit card surface into an optional **D3
knowledge map** — a read-only projection that reveals the *links* the card stack
hides (lineage, corroboration, provenance) and the growth of a dossier over time.

It is downstream of, and must not contradict:

- `CARD_VISUAL_LANGUAGE.md` (presentation contract, invariants);
- `COCKPIT_V3_LIVING_CARDS.md` (V3 surface, projection → renderer chain);
- `../../mvp_vertical/cockpit/projection/cockpit_projection.js` (source of truth for per-card info);
- `../../mvp_vertical/cockpit/projection/child_collection_assembler.js` (containment graph);
- `../../mvp_vertical/cockpit/registries/*.json` (navigation, tags, projection defs);
- Pantheon Next: `KNOWLEDGE_NAVIGATION_UX.md`, `MEMORY.md`.

```text
map view != new data model
map colour != authorization
corroboration != promotion
"called" base != admitted Evidence
runtime pulse != fabricated progress
```

## 1. Scope

The map covers the **knowledge/project domain only** — the objects that have
lineage, corroboration, provenance and temporal accretion:

- in scope: project, information, document, knowledge, work, work_decision,
  project_change_candidate, hermes_run, project_contacts;
- **out of scope (deliberately not a graph)**: tools and competences
  (skills/workflow). These are inventories with orthogonal state, not a growing
  web. They stay a **catalogue + state matrix/radar**; a workflow may use a
  linear spine template. Their relations surface *from* a work node (ego), never
  as a standalone tools graph.

Rationale: a graph is justified only where there are many-to-many links + growth
+ lineage to reveal. Forcing a catalogue into a graph produces a star/hairball —
heavier and less legible than a table.

## 2. Data plumbing

The map is a rendering/layout layer on the **already-normalised in-memory card
models** (`state.cards`, `state.children`). It performs **no fetch of its own**:
it binds to models produced by `cockpit_projection.js`.

Consequence: the ongoing route de-versioning (`/v1/agency/*` → `/agency/*`,
PR #178) and the V2→V3 rename are invisible to the map — they change only
`cockpit/data/cockpit_data_loader.js`, one file below the projection seam.

## 3. Provenance tiers (a load-bearing dimension)

Every node/base carries a provenance tier. The map must never let a lower tier
look like a higher one.

| Tier | Source | Authority |
|---|---|---|
| Evidence | Registre Probatoire (governed) | proof E0–E4, citable |
| Governed fact | PostgreSQL / Agency Data (+ pgvector) | data of record |
| Candidate | Hermès run / RAG retrieval / connector pull | observation, non-probative |
| No authority | mem0 (Hermès memory) | recall only, never citable |

"Part of the project" is not uniform: governed data and project-scoped Registre
entries are durable; mem0 recall and connector (Notion/Google/web) pulls are
**transient context** ("part of the project" only for the duration of a Hermès
query), and must render as injected context, not durable project assets.

## 4. Card families — info, graph type, vocabulary

Shared status vocabulary is the existing `STATUS_LABELS` map (Brouillon · En
rédaction · Acté · Archivé · À valider · Non revu · Prêt · En cours · En attente ·
Terminé · Conflit · Échec · Obsolète · Candidat · À observer).

| Card | Key info carried | Map representation | Links attached | Own vocabulary |
|---|---|---|---|---|
| Space (pantheon/affaires/connaissances/outils) | orientation, counts | root anchor (4 fixed) | containment | Principe · Limite |
| Project | situation en cours, base actée, dossier sensible, suites à donner, revue humaine, schema fields (EUR/m²) | **radial hub / constellation** (families collapsed by default) | root + carries all cross-links | Situation en cours · Dernière base ACTÉE · Dossier sensible · Suites à donner · Revue humaine |
| Information | résumé, détails, source, version, auteur, lineage (`series_id`/`base_acted_id`) | **version chain (lineage)** + node in the flow | containment · lineage · corroboration · provenance(→source) | Modifier avec Hermès · Acter · Nouvelle version · rubrics: Résumé · Informations détaillées · Source · Version source · Auteur |
| Document | structured extraction, pages/tables, anomalies, chunks total/indexed/flagged, source verification | **node + chunk heat** (metrics panel on flip; chunk drill-down = LOD4) | containment · provenance(→info) · chunks | Extraction structurée · Unités · Pages/tableaux · Anomalies · Chunks/indexés · Vérification source |
| Knowledge | title, summary, version, review_status, markdown, tags | **tag cluster** (subject lens; canvas at scale) | containment · provenance(document→knowledge, *to wire*) | Non revu · Référence · consultatif |
| Work | objectif, jalons, chronologie, dernier run, résultat candidat, evidence candidates, traces, resources | **spine / stepper** (milestones + activity) | containment · lineage(→run, →produced info) · ego(→tools/skills) | Objectif · Suivi · Dernier run · Chronologie · Résultat candidat · Jalons · Traces · Limites |
| Work decision | question, résultat présenté, effet demandé, limite | **gate node** (diamond) | link(→work) · salience: validation zone | Refuser · Valider · rubrics: Question · Résultat présenté · Effet demandé · Limite |
| Change candidate | proposal before→after, proposer, base revision, motif, sources | **diff (before→after)** | link(→project fields) · salience: validation zone | À valider · Appliqué · Refusé · rubrics: Proposition · Proposé par · Révision de base · Motif · Sources |
| Hermès run | runtime, scope, started, live status | **live node** (motion, ephemeral) | lineage origin (run→info→doc→knowledge) | Run en cours · Runtime · Scope · Démarré · *no fabricated %* |
| Contacts | grouped people (name·org·role·email·phone) | **grouped network / org chart** (the one place force is justified, stopped after convergence) | containment(project) | Maîtrise d'ouvrage · Maîtrise d'œuvre · Bureaux d'études · Bureau de contrôle · SSI · Entreprises de travaux · Autres intervenants |
| Tool | 6 state axes + permissions/capabilities/evidence/rollback/risks/forbidden | **matrix / radar — NOT a graph** (virtualised catalogue) | referenced *from* work (ego) | Approuvé · Candidat · À observer · Prêt · axes: Installation · État natif · Santé · Gouvernance · Activation · Mise à jour · « installé ≠ approuvé » |
| Competence — skill | capability, `capability_slot` | **catalogue** (list) | referenced *from* work | (like tool, lighter) |
| Competence — workflow | `governed_phases` (sequence) | **linear spine** (template, like `*_spine_d3`) | — | governed phases |

## 5. Link kinds

| Kind | Colour | Style | Cardinality |
|---|---|---|---|
| containment | `#8b98a6` | thin solid | tree |
| lineage (directed) | `#5f83b8` | solid arrow | 1→1 |
| corroboration (support) | `#3fae6d` | solid, width = weight | many-to-many |
| contradiction | `#cf5b5b` | zigzag | many-to-many |
| provenance (base→artifact) | `#aebbcd` | dashed | many-to-many |

Colours reuse the existing `docs/js`-style D3 palette. Corroboration is the
positive end of the existing `contradictory_review` support axis
(`supported / partially_supported / contradicted`); double-validation =
`supported` by ≥2 independent sources.

## 6. Visual channels — reconciled with the card visual language

`CARD_VISUAL_LANGUAGE.md` states **project colour expresses project membership
only** and forbids **glow/shadow/relief**. The map obeys both:

| Dimension | Channel | Reconciliation |
|---|---|---|
| Project / family | **default node colour** (project membership / family palette) | matches the card contract; this is the resting colour |
| Subject (tags) | **opt-in "subject lens"** (registry `color` + `icon_key`) | colour by subject is an explicit analytical mode, **off by default**; selecting a subject saturates its cards and dims the rest |
| Provenance/authority | **border style + opacity + glyph** (Evidence double + seal · Governed solid · Candidate dashed · mem0 ghost) | off hue; new dimension; leaves membership colour intact |
| Status | **separate badge/icon** (unchanged) | keeps the existing "status is a badge" invariant |
| Salience (production / validation / urgent) | **motion (projected events only) + hull outline (stroke) + badge** | **no glow** — hull is a stroke, motion is event-projected (no fabricated activity) |
| Certainty (corroboration) | **ring/arc** around the node | aggregates incoming support without drawing every edge |

Salience is a scarce budget: **max ~5 highlighted zones**, decaying (run ends →
motion off; validation done → hull off); reduced-motion → static ring.

## 7. Levels of detail

| LOD | Trigger | Content | Nodes | Layout | Render |
|---|---|---|---|---|---|
| 0 | start | 4 spaces | 4–5 | anchored (local) | SVG |
| 1 | open space/project | project constellation, **families collapsed** | ~8 meta-nodes | radial / pack | SVG |
| 2 | open a card | family interior (info flow+lineage · work spine · tool matrix) | ≤30 | dedicated | SVG |
| 3 | toggle overlay | provenance (bases) + corroboration | +~12 bases, edges capped | force stopped / bundling | SVG |
| 4 | click doc/base | chunks | 10s–100s → aggregated | drill-down | canvas if massively expanded |

## 8. Budgets (grounded in IFJA fixtures + loader caps)

Real per-project volume (target): ~20–30 documents · ~20 important emails ·
~50 knowledge · 2–7 information · ~4–8 work/decisions/change · ~5 contacts →
**~100–120 items**, plus ~1000 derived chunks.

| Space | Real volume | On screen by default | SVG ceiling | Beyond → |
|---|---|---|---|---|
| project open | ~100–120 items | **~8 meta-nodes** (families collapsed) | ~250–350 expanded nodes | collapse / scope |
| chunks / project | ~1000 | **0** (heat on the document) | — | drill-down one doc |
| connaissances (global) | thousands | scope required | ~1000 | **canvas** |
| affaires (projects) | ≤200 (loader cap) | list / cluster | ~200 | pagination |
| tools / competences | dozens | **table / matrix** (not a graph) | n/a | virtualisation |

Edge budgets: containment + lineage ≈ 1:1 with nodes (negligible). Corroboration
is many-to-many and **not trivial** at ~100 corroborable items per project:
**ego-network by default** (selected node only) + **aggregated certainty ring
always** + **cap ~250 edges** on the full overlay.

## 9. Data gaps to wire before the rich layers

The map is partly ahead of the data. The following must flow before the
dependent layers render anything real:

- lineage fields: `information.derived_from_run_id`,
  `document.derived_from_information_id` (opt. `knowledge.derived_from_document_id`);
- project↔knowledge edge (`source_project_id` on knowledge) for a
  project-centred web (knowledge is currently global-space only);
- positive corroboration signal (only the negative `contradictory_review` exists);
- 4 subject hex tokens to fix (cyan/red/orange/indigo) + light/dark tokens
  (validate against the `dataviz` guidance).

## 10. Sequencing (build small, earn each layer)

The full model above is the target. The build starts as a **thin vertical slice**
and is positioned as a **secondary analysis lens beside the card stack, not a
replacement**.

- **Phase 1 — thin slice (proves the bet).** One project constellation:
  containment + lineage on the acted spine + subject lens. Reads the existing
  projection. SVG only. No corroboration/provenance overlays, no canvas.
  Success test: is it genuinely more useful than the card stack for one real
  task? If not, the navigation is untouched.
- **Phase 2 — provenance + certainty** (gated on lineage fields + a positive
  corroboration signal): provenance tiers, certainty rings, ego corroboration.
- **Phase 3 — provenance-of-consultation layer**: "bases called" reconstructed
  from Context Packs + `trace_refs` + chunk audit identity.
- **Phase 4 — scale**: canvas path for global Connaissances; chunk drill-down at
  volume.

Timing: plan now, **build after** cockpit-v3 / PR #178 land, since they rename
exactly the projection/loader files the map sits above.

## 11. Non-goals

The map does not: fetch data, run or launch a Hermès run, promote memory, admit
Evidence, fabricate progress, merge sources silently, or turn a corroboration or
a "called" base into proof. It is a read-only lens over governed projections.
