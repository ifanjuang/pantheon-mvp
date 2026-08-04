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

The upstream source declares package version `0.20.0`.

## Packaging fact observed on the first live run

Hermes `0.20.0` deliberately refuses wheel and sdist builds:

```text
Building wheels or sdists for hermes-agent is not supported.
Hermes is distributed via the shell installer, Docker image, or Nix.
For development, use an editable source installation.
```

The laboratory therefore does not invent an unsupported wheel. It creates a deterministic `git archive` from the exact release commit, records the archive SHA-256 digest, extracts it into the ephemeral runner and installs that exact source with the upstream-supported editable `uv pip install -e` path.

```text
source archive digest != production installation digest
editable source installed in lab != production installed
```

## Scope

The workflow creates only an ephemeral GitHub-hosted laboratory environment:

```text
fresh HERMES_HOME
fresh Python virtual environment
exact digest-bound source archive
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
archive exact 0.20.0 release source
→ record source archive digest
→ install exact source through supported editable path
→ execute the installed Hermes 0.20.0 CLI
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

## Verified-distribution receipt

The distribution validator now returns a bounded projection of the components whose paths and digests were actually checked:

```text
component_id
kind
source_repository
path
digest_mode
content_digest
required
enabled_by_default
```

This technical projection does not alter the lock, install a component, activate a binding or authorize a task.

## Boundaries

```text
source installed in laboratory != production installed
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
- exact source archive digest is absent;
- distribution composition differs from the three reviewed components;
- profile route differs from `/p/pantheon-governed`;
- any memory axis is active or unknown;
- any tool beyond the two Pantheon context tools is active;
- `X-Hermes-Session-Key` reaches a fixture;
- the outside entity is not refused;
- the binding retries or selects a model/provider;
- the result is accepted, Evidence is admitted or a Project is mutated;
- the plugin is not disabled during rollback;
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
