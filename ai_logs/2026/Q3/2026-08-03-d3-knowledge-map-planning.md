# D3 knowledge map — planning spec

Date: 2026-08-03

## Change

Add a planning specification for an optional, read-only **D3 knowledge map** over
the Cockpit card model: `docs/cockpit/D3_KNOWLEDGE_MAP_PLAN.md`.

The spec defines, per card family, the info carried, the map representation and
its vocabulary; the link kinds (containment · lineage · corroboration ·
contradiction · provenance); the visual channels reconciled with
`CARD_VISUAL_LANGUAGE.md` (project colour = membership, subject colour = opt-in
lens, no glow); LOD thresholds; node/edge budgets grounded in the IFJA fixtures
(~100–120 items and ~1000 chunks per project); and a phased sequencing plan.

Scope decision recorded: the graph covers the knowledge/project domain only.
Tools and competences (skills/workflow) are deliberately **not** a graph — they
stay a catalogue + state matrix; a workflow may use a linear spine.

## Boundary

```text
map view != new data model
map colour != authorization
corroboration != promotion
"called" base != admitted Evidence
runtime pulse != fabricated progress
```

The map binds to the already-normalised in-memory card models
(`cockpit_projection.js`); it performs no fetch, launches no run, promotes no
memory and admits no Evidence. It sits above the projection seam, so the
`/v1/agency/*` → `/agency/*` de-versioning (PR #178) and the V2→V3 rename do not
affect it.

## Data gaps noted (before rich layers)

`information.derived_from_run_id`, `document.derived_from_information_id`, a
project↔knowledge edge, a positive corroboration signal, and 4 subject hex
tokens are required before the provenance/certainty layers render real data.

## Status

Planning specification only — documented, non-implemented in `pantheon-mvp`.
No renderer, endpoint, layout engine or runtime is introduced.
