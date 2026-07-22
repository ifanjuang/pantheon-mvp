"""Cards-first cockpit static composition boundaries."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mvp_vertical import work_issue_read
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
    assert 'data-scene="work"' in response.text

    assert client.get("/cockpit/app.js").status_code == 200
    assert client.get("/cockpit/styles/index.css").status_code == 200
    assert client.get("/editor/").status_code == 200


def test_composed_shell_keeps_existing_api_boundary() -> None:
    client = TestClient(create_cockpit_app(connect_fn=_Connection, api_key="read-key"))

    assert client.get("/health").status_code == 200
    assert client.get("/v1/projects/project-a/documents").status_code == 401
    assert client.get("/v1/projects/project-a/work-issues").status_code == 401


def test_work_issue_route_is_read_only_and_exact_case_scoped(monkeypatch) -> None:
    observed = {}

    def list_projections(_conn, case_ref, *, include_terminal, limit):
        observed.update(
            case_ref=case_ref,
            include_terminal=include_terminal,
            limit=limit,
        )
        return [
            {
                "work_issue": {
                    "issue_id": "issue-1",
                    "case_ref": case_ref,
                    "title": "Review one bounded matter",
                    "status": "review",
                },
                "comments": [],
                "hermes_runs": [],
                "events": [],
                "governance_refs": [],
            }
        ]

    monkeypatch.setattr(work_issue_read, "list_issue_projections", list_projections)
    client = TestClient(create_cockpit_app(connect_fn=_Connection, api_key="read-key"))

    response = client.get(
        "/v1/projects/project-a/work-issues",
        params={"include_terminal": "false", "limit": 25},
        headers={"Authorization": "Bearer read-key"},
    )

    assert response.status_code == 200
    assert response.json()["scope_match"] == "exact_case_ref"
    assert response.json()["work_issues"][0]["work_issue"]["case_ref"] == "project-a"
    assert observed == {
        "case_ref": "project-a",
        "include_terminal": False,
        "limit": 25,
    }
