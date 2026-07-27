"""Read-only Tool Card projection routes for Cockpit V2.

Pantheon governs the semantic axes; this module only serves the concrete MVP
catalogue and optional Hermes runtime observations. It performs no install,
enable, update, approval, activation or task authorization.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

from fastapi import Depends, FastAPI

from .hermes_tool_inventory import observe_hermes_tool_inventory

CATALOG = Path(__file__).resolve().parent / "cockpit" / "tool_catalog.json"


def load_tool_catalog() -> dict:
    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("Tool Card catalogue must contain an items array")
    return payload


def _runtime_observation() -> dict:
    base_url = os.getenv("HERMES_API_URL", "http://hermes:8642").strip()
    api_key = os.getenv("HERMES_API_SERVER_KEY", "").strip()
    return observe_hermes_tool_inventory(base_url, api_key)


def install_tool_card_routes(
    app: FastAPI,
    *,
    require_read_key: Callable,
    observe_runtime: Callable[[], dict] = _runtime_observation,
) -> None:
    @app.get("/v1/tool-cards")
    def tool_cards(_authorized: None = Depends(require_read_key)) -> dict:
        catalog = load_tool_catalog()
        runtime = observe_runtime()
        return {
            "catalog_version": catalog.get("catalog_version"),
            "authority": catalog.get("authority") or {},
            "catalogue": catalog.get("items") or [],
            "runtime_observation": runtime,
            "authorization_inferred": False,
            "activation_changed": False,
            "write_effect": False,
            "non_equivalences": [
                "catalogued != discovered",
                "discovered != installed",
                "installed != approved",
                "native_enabled != scope_activated",
                "healthy != safe",
                "update_available != update_authorized",
                "runtime_success != Evidence",
                "binding_selected != dependency_adopted",
                "watchlist_item != install_instruction",
            ],
        }
