# Tool Card cockpit implementation

Status: partial executable candidate — catalogue projection implemented; live Hermes inventory adapter not yet connected.

This repository owns the concrete Tool Card projection. Pantheon Next owns the governance contract and Capability Slot doctrine.

## Implemented in this branch

- `mvp_vertical/cockpit/tool_catalog.json` is the cockpit-owned supplementary catalogue.
- `mvp_vertical/cockpit/tools.js` adds the `Outils` scene and detailed Tool Cards without duplicating the existing card renderer.
- catalogue records preserve independent installation, runtime, health, governance, update and activation axes.
- LangChain, LangGraph, LangFlow and LangSmith are initial catalogue entries with detailed operational descriptions.
- runtime observations can be injected through `window.PantheonToolCards.setHermesObservations(...)` and are reconciled with catalogue entries.

## Hermes dynamic source boundary

The cockpit does not scan arbitrary Hermes directories itself. A Hermes-version-matched adapter must normalize native inventory, skill files, plugin state, functions/tools, workflows and MCP bindings before injection.

Expected normalized observation shape:

```json
{
  "tool_id": "stable-id",
  "name": "Human label",
  "provenance_mode": "hermes_dynamic_skill",
  "native_identifier": "native-id",
  "source_repository": "owner/repo-or-local-origin",
  "version": "pinned-or-observed-version",
  "installation_state": "installed",
  "native_state": "enabled",
  "health_state": "observed_ready",
  "governance_state": "unreviewed",
  "update_state": "update_unknown",
  "activation_state": "not_activated",
  "observed_at": "2026-07-26T20:00:00Z",
  "capabilities": ["tool-a", "skill-b"],
  "permissions": ["network_access"]
}
```

The adapter is the only layer allowed to know Hermes-specific file paths or manifest formats. This keeps the cockpit stable when Hermes changes its native configuration structure.

## Reconciliation

The first implementation deliberately uses a strict `tool_id` match. It produces:

```text
catalog_only
runtime_only
matched
version_drift
```

Ambiguous records are not silently collapsed. Future adapter work may add explicit stable-native-ID and pinned-source mappings, but must not infer identity from display names alone.

## Non-equivalences

```text
catalogued != installed
installed != approved
native enabled != project activated
healthy != safe
update_available != update_authorized
runtime_success != evidence
```

## Current gap

Live Hermes inventory is not yet wired in this branch. The injection API is implemented so the next Hermes adapter can supply normalized observations without changing the card grammar or hard-coding Hermes file formats into the browser UI.
