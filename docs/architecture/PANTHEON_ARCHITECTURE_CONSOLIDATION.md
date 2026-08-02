# Pantheon architecture consolidation

## Scope

The architecture inventory treats `Pantheon-Next` and `pantheon-mvp` as one governed system.

```text
Pantheon-Next
  governance, doctrine, schemas, authority indexes, scope and approval semantics

pantheon-mvp
  candidate operational implementation, PostgreSQL, APIs, projections and adapters

Hermes
  task execution, skills, tools and external runtimes

Cockpit / OpenWebUI
  user projection and bounded intent capture

Human
  consequential decisions
```

Repository boundaries are architectural boundaries, not naming preferences.

## Target conditions

The consolidation is complete only when:

- one stable name exists for each concept;
- no active module, schema identity, route family or package is named by generation;
- one repository owns each authoritative contract;
- vendored schemas remain pinned derivatives, never competing authorities;
- one executable path exists for each function;
- compatibility code has a named consumer and removal condition;
- unused code is removed only after import, route, packaging, test, deployment and doctrine checks;
- Cockpit projections do not dictate backend semantics;
- adapters remain optional and replaceable;
- Pantheon does not become runtime, scheduler, queue, provider router, installer, plugin manager, memory engine or automatic approval system.

## Finding classification

Every inventory finding receives one final disposition:

```text
keep
simplify
merge
move
 deprecate
 delete
uncertain
```

A finding is not deletion proof.

## Review order

1. Ownership contradiction or authority duplication.
2. Duplicate schema identity or semantic model.
3. Generation/version names in active architecture.
4. Multiple executable paths for one responsibility.
5. Compatibility and legacy seams without active consumers.
6. Misclassified modules, routes, docs and adapters.
7. Performance costs: repeated validation, repeated registry loading, N+1 reads, duplicate HTTP clients and long transactions.
8. Cosmetic naming and directory cleanup.

## Cross-repository command

With sibling checkouts:

```bash
python tools/audit_pantheon_architecture.py \
  --pantheon-next-root ../Pantheon-Next \
  --pantheon-mvp-root . \
  --output docs/architecture/PANTHEON_ARCHITECTURE_INVENTORY.md
```

The generated inventory is report-only. Structural changes are made in separate, bounded pull requests after the relevant ownership and runtime boundaries are verified.
