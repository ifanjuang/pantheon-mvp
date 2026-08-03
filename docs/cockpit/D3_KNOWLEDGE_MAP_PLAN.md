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
  project_change_candidate, hermes_run;
- **contacts** are **project info**, rendered as a **facet of the Project card**
  (a section / flip group), not a standalone graph node — this removes the only
  `d3-force` case, so the whole map is static hierarchy + chains (no force
  anywhere);
- **out of scope (deliberately not a graph)**: tools and competences
  (skills/workflow). These are inventories with orthogonal state, not a growing
  web. They stay a **catalogue + state matrix/radar**; a workflow renders as a
  **linear chain or an action DAG** (node = action, edge = order/dependency)
  depending on whether its `governed_phases` branch. Their relations surface
  *from* a work node (ego), never as a standalone tools graph.

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

## 2a. Swappable layout system (graph type is pluggable)

The map is layered **model → layout → render**, and the **layout must be
swappable at runtime** without touching the model or the renderer.

- a **layout registry** keyed by name: `radial`, `grid`, `chain`
  (lineage), `cluster` (by subject, organic hulls), `dag` (workflow actions),
  `bundle` (hierarchical edge bundling — support overlay), `matrix`
  (tools, non-graph);
- each strategy is a **pure function** `(graphModel, opts) -> positionedNodes`;
- a **default layout per scope / card kind**, plus a **user override**:

  | Scope / kind | Default layout | Why |
  |---|---|---|
  | Project (overview) | **radial** (families as satellites) | the project is a hub; a family overview |
  | Documents | **chain** (lineage) | documents are versioned (revision indices) |
  | Information | **chain** (lineage) | version series (`series_id` / `base_acted_id`) |
  | Knowledge | **grid** (dense scan, sorted) | large corpus (~50/project, thousands global) |
  | Subject view (transverse) | **cluster** (organic hulls) | "everything on subject X", available everywhere as the subject lens |
  | Workflow (competence) | **chain or DAG** | sequential vs branching `governed_phases` |

  Nodes render **without a central hub** (sub-cards are the primary nodes); a
  group is read from its **organic hull** + label, not a hub node.
- switching layout changes **positions only** → animate with a transition; hulls
  are recomputed each frame for an organic morph; the model and read contract are
  untouched;
- adding a graph type = one new strategy module + one registry line. Nothing
  else changes.

This is what makes "changing graph type" cheap and is the reason no force layout
is required (all strategies are deterministic/static).

## 2b. Harmonized read contract (dates · structuration · retrieval)

Because several executor tools (Docling / Marker / chunkers / retrieval paths)
fill the data, the map reads **one normalized schema**, harmonized **below the
map** (in the projection + the extraction/retrieval contracts). The map never
sees tool-specific shapes.

- **Dates** — one canonical `timestamp` + `date_kind`
  (created / updated / acted / occurred / observed / started), resolved once for
  every family (generalising the existing `informationTimestamp` fallback
  `information_date || acted_at || updated_at || created_at`). Timelines and
  lineage order are consistent; the map does no per-family date guessing.
- **Structuration** — one normalized structural-unit schema (`content_type`,
  `section_path`, `parent_heading`, `page_start/end`, `quality_flags`,
  `table_data`), the `extraction_units` shape, that every converter maps into.
- **Retrieval** — one normalized relevance record (`score`, `semantic_rank`,
  `lexical_rank`, `methods`) across retrieval paths (hybrid fusion already
  provides it), read only in the query-result mode.

Principle: harmonisation lives under the map, so the map stays tool-agnostic
(§ tool choice) and layout-swappable (§ 2a) over a stable contract.

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
| Contacts | grouped people (name·org·role·email·phone) | **Project facet** (a grouped section / flip of the Project card) — **not a graph node**, no force | belongs to project (facet) | Maîtrise d'ouvrage · Maîtrise d'œuvre · Bureaux d'études · Bureau de contrôle · SSI · Entreprises de travaux · Autres intervenants |
| Tool | 6 state axes + permissions/capabilities/evidence/rollback/risks/forbidden | **matrix / radar — NOT a graph** (virtualised catalogue) | referenced *from* work (ego) | Approuvé · Candidat · À observer · Prêt · axes: Installation · État natif · Santé · Gouvernance · Activation · Mise à jour · « installé ≠ approuvé » |
| Competence — skill | capability, `capability_slot` | **catalogue** (list) | referenced *from* work | (like tool, lighter) |
| Competence — workflow | `governed_phases` (sequence or branching) | **linear chain** (like `*_spine_d3`) **or action DAG** (node = action, edge = order/dependency) | — | governed phases |

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
| 3 | toggle overlay | provenance (bases) + corroboration | +~12 bases, edges capped | ego + bundling (no force) | SVG |
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

**Support-overlay renderer — candidate: hierarchical edge bundling (`bundle`).**
For a *global* view of the corroboration / contradiction web across Information +
Documents + Knowledge (many-to-many, sharing the project→family→item or subject
hierarchy), hierarchical edge bundling is the right renderer — deterministic (no
force), grouped by subject like the clusters. Scope: **support overlay only**,
never lineage (1→1) nor Pantheon (few directed links). It is **Phase 2/3 and
gated on edge density, not node count**: the positive corroboration signal does
not exist yet (only the negative `contradictory_review`), so today the ring
would render empty. Bascule rule: once corroboration is populated, measure
density — rich → `bundle` as an audit/relations view; sparse → stay on
ego-network + certainty rings.

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

## 10a. Technical & aesthetic details

Decisions and known risks below the section level.

**Colour is not a subject key (critical).** The `tag_registry` collapses ~33
subjects onto ~9 colour tokens, so **two subjects in the same view can share a
colour**. Therefore:
- the **subject icon (`icon_key`) is mandatory**, not optional — colour + icon
  together identify a subject;
- within a scope, if two visible subjects share a token, disambiguate by icon
  (and optionally a secondary tint/pattern);
- icons must be **inline SVG** (the CSP blocks font CDNs — no Material Symbols
  webfont), shipped as a small symbol sheet.

**Subject lives on cards, not chunks.** `subject_tags` exists on Information
(agency data) and on Documents (`document_classifications`), consumed by card
projections. `extraction_units` / `retrieval_chunk_projections` have **no
subject** — a chunk's channel is `content_type`
(heading/paragraph/list/table/figure/page); a chunk inherits its document's
subject only if tinted.

**Tag coverage degrades gracefully.** `subject_tags` defaults to `[]`; the lens
cannot invent a subject. Untagged item → **neutral membership colour** or a
"non classé" bucket. Colour quality tracks classification coverage.

**Channels stay orthogonal & redundant.** subject = colour **+ icon** · family =
shape/icon · provenance = border/opacity/glyph (off hue) · status = badge · a
same-token disambiguation never leaks into the provenance or status channels.

**Palette.** Per-theme subject tokens (light/dark variants — some hues go muddy
on dark); ensure the present subjects are perceptually separable; neutral has a
slate-blue bias (chosen, not pure grey); membership colour muted so it never
fights subjects.

**Layouts are pure & deterministic.** No force; any jitter is seeded. Positions
memoised per (layout, node-set); layout choice persisted; enter/exit handled
(enter from parent centroid, exit fade), not only position tweens.

**Rendering.** SVG ≤ ~1.5k marks → **canvas beyond** (Knowledge at scale), shared
model/layout, quadtree hit-testing on canvas. **Zoom/pan + semantic zoom** for
large scopes. Hulls: convex-smoothed by default; **concave hull / metaballs** if
a truly organic blob is wanted (convex encloses empty space). At high density,
prefer a status **arc segment** over a corner dot and a **ring notch** over a
floating "!", to avoid collisions.

**Motion.** ~600 ms ease-in-out (no bounce — reads AI-generic); hull morph on
switch is the signature moment; **no idle/ambient animation** except the
observed live-run pulse; reduced-motion snaps; no hover animation (card
contract).

**Accessibility.** Keyboard in SVG is real work: `tabindex`/`role`/`aria-label`
on node groups, arrow navigation, enter to open, escape to reset, visible focus
ring. Hover ≠ selection ≠ focus (three distinct visual states). Nothing essential
behind hover only.

## 10b. Improvement backlog (additional info to exploit)

Ranked by value × data availability. "Now" = no new data required.

**Available now (no new data):**
- **Node size = magnitude** — `page_count` / `chunk_count` / `unit_count` (√-scaled): a quantitative channel; big documents and long lineages stand out.
- **Freshness + time scrubber** — harmonised `timestamp`: fade old items and replay the dossier's accretion over time ("au fil de l'eau").
- **Salience / exergue mode** — `status` + `anomaly_count`/`quality_flags` + human-review set (decisions, change_candidates, `needs_review`): the actionable "where to look" layer (production / validation / urgent).
- **Second facet: type** — `type_tags` (email, plan, contrat, cctp, dce…): a "type lens" alongside the subject lens.
- **Search / filter** — subject · type · status · author · date · text.
- **Author** — `author`: filter/cluster by who produced.
- **Tool provenance in inspector** — `converter` + `converter_version`, `contract_id`, `ingestion_id`: the one place the ingestion tool is visible.

**Contextual (available, meaningful in a mode):**
- **Query-result mode** — retrieval `distance` / `semantic_rank` / `lexical_rank` when Hermès queries: highlight retrieved items + rank.
- **Chunk drill-down** — `content_type` / `section_path` / `table_data` / `quality_flags` (gated `compilation_id`).
- **Live work** — milestones + activity `occurred_at` + running-run pulse.

**Gated on missing data (wire first):**
- run→info→doc→knowledge lineage (`derived_from_*`);
- corroboration/contradiction positive signal → unlocks `bundle` (HEB);
- project↔knowledge edge.

**Cross-cutting UX/tech:** zoom/pan + semantic zoom; arrow-key node navigation; multi-select / compare; scope breadcrumb; light hover tooltip vs pinned inspector.

Highest-ROI now: **node size = magnitude**, **freshness + time scrubber**, **salience/exergue**, **type facet + search** — the first two are prototyped in the demo.

## 11. Non-goals

The map does not: fetch data, run or launch a Hermès run, promote memory, admit
Evidence, fabricate progress, merge sources silently, or turn a corroboration or
a "called" base into proof. It is a read-only lens over governed projections.
