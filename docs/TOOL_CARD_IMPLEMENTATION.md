# Tool Card cockpit implementation

Status: partial executable candidate — catalogue projection and verified Hermes inventory normalization implemented; cockpit server route not yet connected.

This repository owns the concrete Tool Card projection. Pantheon Next owns the governance contract and Capability Slot doctrine.

## Implemented in this branch

- `mvp_vertical/cockpit/tool_catalog.json` is the cockpit-owned supplementary catalogue.
- `mvp_vertical/cockpit/tools.js` adds the `Outils` scene and detailed Tool Cards without duplicating the existing card renderer.
- catalogue records preserve independent installation, runtime, health, governance, update and activation axes.
- LangChain, LangGraph, LangFlow and LangSmith are initial catalogue entries with detailed operational descriptions.
- runtime observations can be injected through `window.PantheonToolCards.setHermesObservations(...)` and are reconciled with catalogue entries.
- `mvp_vertical/hermes_tool_inventory.py` reads only the verified Hermes discovery surfaces `/v1/skills`, `/v1/toolsets` and `/v1/capabilities` and normalizes them into Tool Card observations.

## Hermes dynamic source boundary

The cockpit does not scan arbitrary Hermes directories itself. The adapter uses the authenticated, read-only Hermes API rather than guessing internal file paths or manifest formats.

The current verified normalization covers:

```text
/v1/skills        -> hermes_dynamic_skill records
/v1/toolsets      -> hermes_native_inventory records with exposed tools
/v1/capabilities  -> Hermes API Server record with active API features
```

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
  "permissions": []
}
```

Unknown governance, permissions, update and activation information is not inferred from Hermes runtime presence. In particular, a listed or enabled skill remains `unreviewed` and `not_activated` from Pantheon's point of view.

## Reconciliation

The first implementation deliberately uses a strict `tool_id` match. It produces:

```text
catalog_only
runtime_only
matched
version_drift
```

Ambiguous records are not silently collapsed. Future adapter work may add explicit stable-native-ID and pinned-source mappings, but must not infer identity from display names alone.

## Responsibility split

```text
Hermes: owns native skill/toolset/runtime discovery and execution.
MVP observer/adapter: reads verified discovery APIs and normalizes observations.
Cockpit/OpenWebUI: displays the resulting Tool Cards.
Pantheon: governs classification, scope, approval, evidence, activation and lifecycle decisions.
Human: approves consequential adoption, activation and update.
```

The adapter performs no POST, install, enable, update, approval or execution operation.

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

The normalized Hermes adapter is implemented and contract-tested. The remaining integration step is to expose it through the authenticated MVP observer/cockpit route expected by `tools.js` (`/v1/hermes/capabilities`). Until that route is connected, the browser correctly reports the adapter as not connected rather than inventing runtime state.
