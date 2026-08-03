# Cockpit knowledge map (read-only lens)

Status: implemented candidate — a bounded, read-only visual lens over the
existing Cockpit projection. Not wired into the live cockpit page yet.

## Invariants

```text
map view != data model
projection != authority
read-only : no fetch, no mutation, no run launch, no memory promotion
```

The map reshapes and draws the **already-normalised** card graph. It decides
nothing and admits nothing.

## What it binds to

The in-memory projection produced by `../projection/cockpit_projection.js`:

- `state.cards` — `Map<entity_id, cardModel>`;
- `state.children` — `Map<parentId, entity_id[]>`.

It reads only projected card fields (`entity_id`, `entity_type`,
`presentation_family`, `title`, `status`, `date`, `subject_tags`, `series_id`,
`base_acted_id`, `source_run_id`). It does **not** call the HTTP API, so the
stable-route convergence (no `/v1`) does not affect it — the map sits above the
transport seam.

## Modules

- `map_graph_model.js` — pure `build(cards, children) -> { nodes, links }`.
  Links: `containment` (parent→child) and `lineage` (version series /
  `base_acted_id`). `node.origin` records the factual source
  (`agency` / `knowledge` / `hermes`) — it is **not** an authority claim.
- `map_layouts.js` — swappable layout registry, each a pure
  `(nodes, opts) -> {id:{x,y}}` (`cluster`, `radial`, `grid`, `chain`).
  Deterministic, no force. Add a graph type = add one entry.
- `map_view.js` — read-only SVG renderer: `create(svg, {cards, children}, opts)`
  → `{ setLayout, setGroupBy, render, destroy }`.

## Default layout per scope (caller's choice)

```text
project (overview)  -> radial (family satellites)
documents           -> chain  (revision lineage)
information         -> chain  (version lineage)
knowledge           -> grid   (dense scan)
subject view        -> cluster (organic grouping)
```

## Deliberately out of this slice

Metaballs, subject-colour lens, provenance tiers, time scrubber, magnitude
sizing, corroboration overlay (hierarchical edge bundling) and canvas scaling
are demonstrated in the standalone prototype and are later phases — several are
gated on data not yet wired (`derived_from_*`, a positive corroboration signal).
Live-cockpit mounting is intentionally deferred until the convergence
(stages L–O) stabilises; it will read the same projection through a small hook.

## Try it

Open `demo.html` — it builds a small in-memory `{cards, children}` and mounts the
view. No network, no build step.
