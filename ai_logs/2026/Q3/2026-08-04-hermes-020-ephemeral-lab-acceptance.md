# Hermes 0.20.0 ephemeral laboratory acceptance — 2026-08-04

Status: candidate implementation on a feature branch. No agency, NAS or production installation has been observed.

## Objective

Execute the reviewed Pantheon ↔ Hermes distribution against an actual Hermes Agent `0.20.0` installation without requiring or exposing production credentials.

## Verified authorities

```text
Hermes upstream commit
3c27eb6234bf91b8ceee9e9071591b31e9b148cb

Pantheon-Next authority
 db5506668f06bab05b0cad1b244ff19ab17b5f52

pantheon-mvp implementation baseline
898eb21a4cb48f8302cb32f02c3240a9867df43e
```

The upstream source declares package version `0.20.0`. The acceptance builds a wheel from the exact commit, records its SHA-256 digest, installs that wheel in a fresh Python 3.12 virtual environment and executes the installed `hermes` command.

## Scope

The workflow creates only an ephemeral GitHub-hosted laboratory environment:

```text
fresh HERMES_HOME
fresh Python virtual environment
one default multiplexing gateway
one pantheon-governed profile
one locally installed Pantheon context plugin
one deterministic local OpenAI-compatible fixture
one deterministic bounded Pantheon API fixture
one synthetic read-only admission
```

No repository secret, cloud model key, production endpoint or self-hosted runner is used.

## Acceptance path

```text
build exact 0.20.0 wheel
→ record wheel digest
→ install wheel
→ verify three-component Pantheon lock
→ create isolated profile
→ configure all memory axes off
→ install plugin disabled
→ inspect plugin copy
→ enable plugin explicitly
→ start real multiplexing gateway
→ observe /p/pantheon-governed
→ qualify exact two-tool surface
→ recapture fresh memory receipt
→ launch one synthetic admitted run
→ read active Context Pack manifest
→ read one admitted entity
→ verify refusal of one outside entity
→ reconcile once
→ disable plugin
→ stop gateway
→ verify profile route is unreachable
```

## Boundaries

```text
wheel installed != production installed
lab route qualified != agency route qualified
synthetic run completed != result accepted
runtime return recorded != Evidence admitted
plugin enabled in lab != production binding activated
rollback in lab != production rollback verified
```

The distribution lock remains a candidate. The lab summary must state:

```text
target_installation_observed = false
production_activated = false
future_tasks_authorized = false
result_accepted = false
evidence_admitted = false
```

## Criteria

The workflow fails closed when any of these is observed:

- Hermes version differs from `0.20.0`;
- wheel digest is absent;
- distribution composition differs from the three reviewed components;
- profile route differs from `/p/pantheon-governed`;
- any memory axis is active or unknown;
- any tool beyond the two Pantheon context tools is active;
- `X-Hermes-Session-Key` reaches a fixture;
- the outside entity is not refused;
- the binding retries or selects a model/provider;
- the result is accepted, Evidence is admitted or a Project is mutated;
- the gateway route remains reachable after rollback.

## Remaining production proof

Even after a successful lab run, `pantheon-mvp#227` remains open for:

```text
agency/NAS Hermes artifact digest
real pantheon-governed profile
real OpenWebUI path
real Pantheon API and admission
real operator identity
real activation scope and expiry
real rollback target and proof
```
