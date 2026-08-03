# Runtime profile and observation boundary

## Purpose

Normalize what an external runtime reports without making pantheon-mvp a runtime, scheduler, provider router, plugin manager, memory system or approval engine.

## Contract

`mvp_vertical.runtime_profile` validates two adapter-boundary objects:

- an observed runtime profile;
- an observed runtime event.

Capability names remain adapter data. The MVP validates only the support-state vocabulary so release-specific features do not become backend identities by accident.

## Ordering

```text
binding candidate
-> installation
-> health
-> compatibility
-> update review
-> activation
-> task authorization
-> execution observation
```

## Invariants

```text
reported != observed
healthy != compatible
compatible != safe
compatible != activated
activated != task_authorized
completed observation != accepted result
runtime_success != Evidence
```

## Hermes v2026.8.3

The release can be represented by the existing external runtime binding with `runtime_version=v2026.8.3` and adapter-reported capabilities such as background execution, delegation or learning-loop support.

No Hermes-specific branch is present in the normalizer. Another external runtime can provide the same bounded object shape.
