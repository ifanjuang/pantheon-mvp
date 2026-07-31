# Cockpit CSS clean-slate rebuild

## Decision

The Cockpit visual layer is rebuilt from a clean CSS authority instead of continuing to override historical V2/V3 styles.

The JavaScript navigation, CockpitSnapshot contract, renderer DOM, schemas, editors, provenance, status and authorization semantics remain unchanged unless a separate reviewed change proves that a DOM adjustment is required.

```text
CSS rebuild != Cockpit architecture rewrite
visual projection != semantic model
UI status != authorization
```

## Target stylesheet order

```text
cockpit_tokens.css
cockpit_reset.css
cockpit_shell.css
cockpit_navigation.css
cockpit_card_base.css
cockpit_card_blobs.css
cockpit_card_families.css
cockpit_card_states.css
cockpit_editors.css
cockpit_responsive.css
```

Each visible property has one authority. Family styles provide variables and signatures; they do not redefine geometry or navigation.

## Scope to retire

The new entry point must stop loading the historical visual cascade once equivalent coverage exists:

- `styles/index.css`
- `styles/v2.css`
- `styles/v2_refinement.css`
- `styles/v2_swiper.css`
- `styles/v2_shell_controls.css`
- `styles/v3_living_cards.css`
- `styles/v3_geometry.css`
- `styles/v3_collections.css`
- the transitional family files introduced before the clean-slate consolidation

Editor-specific styles are migrated into the new layer before their old files are removed. No historical stylesheet remains loaded as a fallback after cutover.

## Visual grammar retained

- Pack / Booster / Card hierarchy.
- Pantheon: three organic CSS outline blobs, cyan / yellow / magenta.
- Affaires: three filled organic blobs.
- Project booster: white surface and project-colour blob composition.
- Work: white surface with a 12 × 12 px project-colour corner.
- Folder: white surface with a 12 px project-colour top band.
- Knowledge and Skills: full-card gradients with no card border on the front.
- General-card backs: 4 px coloured border.
- Business/project-card backs: 1 px coloured border.
- No shadows, glow, paper texture, hover animation or swipe animation.

## Migration sequence

1. Inventory every class and computed responsibility used by the current DOM and tests.
2. Add the clean-slate styles alongside the old cascade behind `data-cockpit-css="next"`.
3. Rebuild shell and fixed viewport geometry.
4. Rebuild Swiper host geometry without changing MotionAdapter ownership.
5. Rebuild the common card front/back structure.
6. Apply family signatures and project inheritance.
7. Migrate editors and overlays.
8. Switch the canonical page to the new styles only.
9. Delete retired files and stale tests.
10. Verify demo/live, mobile/desktop, keyboard, flip, swipe, nested descent, New card and editor interactions.

## Acceptance

- one visible CSS authority per responsibility;
- no old stylesheet loaded by the canonical page;
- no family-specific geometry override;
- no renderer dependency on stylesheet filenames;
- no Swiper API outside MotionAdapter;
- bounded mounted projections remain unchanged;
- demo and live use the same visual entry point;
- full CI green plus browser verification at representative mobile and desktop widths.
