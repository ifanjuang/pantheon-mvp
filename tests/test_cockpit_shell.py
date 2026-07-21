"""Cards-first cockpit static composition boundaries."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mvp_vertical.cockpit_shell import create_cockpit_app


class _Connection:
    def close(self) -> None:
        pass


def test_cards_first_cockpit_shell_is_available() -> None:
    client = TestClient(create_cockpit_app(connect_fn=_Connection, api_key="read-key"))

    response = client.get("/cockpit/")
    assert response.status_code == 200
    assert "Pantheon Cockpit" in response.text
    assert "Le cockpit affiche des projections" in response.text

    assert client.get("/cockpit/app.js").status_code == 200
    assert client.get("/cockpit/styles/index.css").status_code == 200
    assert client.get("/editor/").status_code == 200


def test_composed_shell_keeps_existing_api_boundary() -> None:
    client = TestClient(create_cockpit_app(connect_fn=_Connection, api_key="read-key"))

    assert client.get("/health").status_code == 200
    assert client.get("/v1/projects/project-a/documents").status_code == 401
