# Cross-repository Pantheon architecture audit

The architecture inventory considers `Pantheon-Next` and `pantheon-mvp` together.

## Canonical ownership

- `Pantheon-Next`: doctrine, governed concepts, schemas, statuses, Evidence, scope, approvals and Capability Slots.
- `pantheon-mvp`: PostgreSQL, APIs, executable projections, adapters and bounded integration seams.
- Hermes or another selected external runtime: execution, tools, provider routing and runtime-local state.
- Cockpit/OpenWebUI: interaction and projection only.

## Review dimensions

Every active artifact is reviewed for:

- generation-named paths or identities;
- exact duplicates and repeated names across repositories;
- competing definitions of one governed concept;
- implementation placed in governance or governance semantics redefined in implementation;
- obsolete compatibility paths;
- files without a demonstrated active consumer;
- incorrect folder placement;
- opportunities to retain, simplify, merge, move, deprecate or remove.

A finding is not deletion proof. Removal requires evidence that no active import, route, script, deployment, schema, documentation authority or compatibility obligation remains.

## Naming rule

Active architecture names are responsibility-based. `v0`, `v1`, `v2`, `v3`, `legacy`, `next` and similar generation labels are not permanent identities for modules, routes, schemas, projections or folders. Ordered database migration identifiers may remain where required to preserve migration history.

## Convergence rule

One governed concept has one canonical owner and one canonical definition. Other repositories may implement, vendor, project or adapt the definition, but must not redefine its semantics.

## Usage

With sibling checkouts:

```bash
python tools/audit_pantheon_architecture.py \
  --repository pantheon-mvp=implementation=/path/to/pantheon-mvp \
  --repository Pantheon-Next=governance=/path/to/Pantheon-Next \
  --output docs/architecture/PANTHEON_ARCHITECTURE_INVENTORY.md
```

The report exposes candidates for human classification. It performs no rewrite, move or deletion.
