# Cockpit cleanup sequence

## Authority

This sequence changes presentation and entrypoint structure only. It does not alter governance, authorization, Evidence, ChangeCandidate semantics, or the CockpitSnapshot contract.

## Stage 1 — retired visual authorities

The canonical page loads only:

- `styles/cockpit.css`
- `styles/cards.css`
- `styles/families.css`
- `styles/editors.css`

Historical V2/V3 visual experiments are removed once no HTML, JavaScript, test fixture, or published regression surface references them.

## Stage 2 — neutral entrypoints

The active chain is named by responsibility rather than implementation generation:

- `cockpit_bootstrap.js`
- `live_bootstrap.js`
- `live_collection_adapter.js`
- `shell_controls.js`

This stage is intentionally limited to filenames and imports. Functional DOM identifiers and the live schema renderer remain unchanged until their consumers are migrated.

## Stage 3 — neutral renderer contract

The live renderer will emit the canonical classes directly:

- `card`
- `card-inner`
- `card-face`
- `card-front`
- `card-back`
- semantic content primitives

Only after that migration may `CLASS_MAP` and legacy class normalization be removed from `live_collection_adapter.js`.

## Stage 4 — functional DOM identifiers

Historical `v2-*` element identifiers are renamed only after every consumer is enumerated and migrated in the same change. IDs are functional hooks, not visual styling APIs.

## Invariants

```text
visual projection != semantic model
UI status != authorization
installed != approved
runtime_success != Evidence
```

The CSS owns graphical projection. HTML and JavaScript own structure, content, state and interaction. Swiper remains isolated behind the collection motion boundary.
