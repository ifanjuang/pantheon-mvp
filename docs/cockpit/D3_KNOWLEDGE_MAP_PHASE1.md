# Cockpit D3 knowledge map — Phase 1 (thin slice) spec

Status: planning specification — documented, non-implemented in `pantheon-mvp`.
Boundary profile: candidate design note. No renderer, endpoint or runtime is
introduced. This refines Phase 1 of `D3_KNOWLEDGE_MAP_PLAN.md` into an
implementable slice, without prescribing code.

## 1. Goal and the bet it must prove

Ship the **smallest map that could be genuinely more useful than the card
stack** for one real task, as a **secondary analysis lens** — never a
replacement for navigation.

Success test (must be decided before building the rest): using only Phase 1, a
user can answer *faster than with the card stack* at least one of:

- "show me the version lineage of this Information" (draft → acted → superseded);
- "show me everything on subject X in this project" (subject lens).

If neither wins against the card stack, navigation is untouched and we stop.

## 2. Scope

In scope:

- one **project constellation** (the selected project);
- **containment** backbone (project → families → items), families **collapsed by
  default** into meta-nodes with counts;
- **version lineage** edges only — the lineage that already exists in data
  (`series_id` / `base_acted_id` on Information);
- **subject lens** (opt-in) using `tag_registry` colour + icon;
- **SVG only**, static hierarchical layout (no force).

Explicitly out of scope for Phase 1 (later phases):

- corroboration / contradiction overlays;
- provenance tiers rendering and the "bases called" layer;
- run→info→doc lineage (needs `derived_from_*` fields that do not exist yet);
- chunks, canvas, live-run motion, mem0 / connectors;
- tools / competences (never a graph).

## 3. Data contract (read-only, over the projection seam)

Phase 1 **reads the already-normalised in-memory models** and performs **no
fetch of its own**. It consumes, from the existing projection
(`cockpit_projection.js` + `child_collection_assembler.js`):

- `state.cards` (Map of card models) and `state.children` (parent → child ids);
- per card: `entity_id`, `entity_type`, `family` / `presentation_family`,
  `status`, `date`, `title`, `subject_tags`, `identity_accent`;
- for lineage: `series_id`, `base_acted_id` (Information only).

Because it sits above the loader, the `/v1/agency/*` → `/agency/*` de-versioning
(PR #178) and the V2→V3 rename change nothing here — they touch
`cockpit/data/cockpit_data_loader.js`, one layer below.

The map never writes, never launches a run, never promotes memory, never admits
Evidence.

## 4. Suggested module shape (layered, for testability)

A dedicated, self-contained folder keeps the slice out of the renamed files:

```text
cockpit/map/
  map_graph_model.js   pure: (state.cards, state.children) -> {nodes, links}
  map_layout.js        pure: {nodes,links} -> positioned nodes (d3-hierarchy)
  map_render.js        SVG draw + enter/update/exit
  map_subject_lens.js  subject saturate/dim from tag_registry
  map_view.js          wiring + toggle (lens surface, not navigation)
```

`map_graph_model.js` must be a **pure function** so it is unit-testable against
the IFJA fixtures without a browser (parity: fixtures → expected nodes/links),
mirroring the existing `test_cockpit_v2_*` discipline.

## 5. Layout

- **Radial hub**: project at centre; N2 families as **collapsed meta-nodes**
  (`Contacts`, `Informations (n)`, `Documents (n)`, `Travaux (n)`) → ~5–8 nodes
  at rest even for a ~120-item project.
- **Expand a family** → its items around that meta-node (LOD2), still `d3-hierarchy`
  (pack/tree), **no force**.
- **Version lineage**: within the Information family, chain items by
  `series_id`; mark the `base_acted_id` node as the acted spine anchor.

## 6. Visual channels (Phase 1 subset, obeying `CARD_VISUAL_LANGUAGE.md`)

| Dimension | Channel | Note |
|---|---|---|
| Project / family | default node colour (`identity_accent` / family palette) | membership only, per the card contract |
| Subject (tags) | **opt-in lens**: select subject → saturate matching, dim rest | colour from `tag_registry`; **off by default** |
| Status | separate badge/icon | unchanged invariant |
| Lineage | directed link `#5f83b8`, acted anchor emphasised by ring | version chain only |

No glow/shadow (invariant). No motion in Phase 1 (live-run pulse is a later
phase). Reduced-motion trivially satisfied.

## 7. Interaction

- open the map as a **toggled lens** over the current project (not a route change);
- click meta-node → expand/collapse family;
- click item → reuse the **existing card flip / detail** (no new detail surface);
- subject lens → pick a subject chip → saturate/dim; clear → back to membership colour;
- escape / toggle off → return to the card stack unchanged.

## 8. Budgets (Phase 1)

- default on screen: ~5–8 meta-nodes;
- one family expanded: typically ≤ 30 items (fixtures: Information ≤ 7; real
  Documents ≤ 30);
- fully expanded worst case ~120 items × ~4 marks ≈ ~500 marks ≪ SVG ceiling
  (~1500). No canvas needed in Phase 1.

## 9. Definition of done

1. From a selected project, the constellation renders from the projection with no
   extra network call;
2. families are collapsed by default and expand on click;
3. Information version lineage is visible and the acted anchor is distinguishable;
4. the subject lens saturates/dims correctly from `tag_registry`, colour off by
   default;
5. status stays a badge; no glow; membership colour is the resting colour;
6. `map_graph_model.js` has fixture-based parity tests;
7. the map is a toggled lens; turning it off leaves navigation untouched;
8. the success test (§1) is evaluated on a real dossier before Phase 2 is opened.

## 10. Non-goals (restated)

No fetch, no run launch, no memory promotion, no Evidence admission, no
corroboration/provenance/chunks/canvas/mem0/connectors, no tools-or-competences
graph. Build after cockpit-v3 / PR #178 land.
