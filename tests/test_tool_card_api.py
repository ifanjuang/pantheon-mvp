from fastapi import FastAPI
from fastapi.testclient import TestClient

from mvp_vertical.tool_card_api import install_tool_card_routes, load_tool_catalog


def test_catalogue_loads_packaged_tool_records():
    catalog = load_tool_catalog()
    assert catalog["catalog_version"] >= 2
    ids = {item["tool_id"] for item in catalog["items"]}
    assert {"haystack", "llamaindex", "langchain", "langgraph", "hermes-api-server"} <= ids


def test_tool_card_route_is_read_only_and_keeps_runtime_observation_qualified():
    app = FastAPI()

    def read_key():
        return None

    def observed():
        return {
            "status": "not_configured",
            "observed_at": "2026-07-27T05:00:00Z",
            "capabilities": [],
        }

    install_tool_card_routes(app, require_read_key=read_key, observe_runtime=observed)
    response = TestClient(app).get("/v1/tool-cards")
    assert response.status_code == 200
    payload = response.json()
    assert payload["runtime_observation"]["status"] == "not_configured"
    assert payload["authorization_inferred"] is False
    assert payload["activation_changed"] is False
    assert payload["write_effect"] is False
    assert "installed != approved" in payload["non_equivalences"]

    methods = {
        method
        for route in app.routes
        if getattr(route, "path", None) == "/v1/tool-cards"
        for method in (getattr(route, "methods", None) or set())
    }
    assert methods == {"GET"}
