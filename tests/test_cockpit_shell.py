"""Cards-first cockpit static composition boundaries."""

from __future__ import annotations

from fastapi.testclient import TestClient

from mvp_vertical import effect_preview, work_issue_read
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
    assert 'src="effects.js"' in response.text
    assert 'src="knowledge_updates.js"' in response.text

    assert client.get("/cockpit/app.js").status_code == 200
    assert client.get("/cockpit/effects.js").status_code == 200
    assert client.get("/cockpit/knowledge_updates.js").status_code == 200
    assert client.get("/cockpit/styles/index.css").status_code == 200
    assert client.get("/cockpit/styles/effects.css").status_code == 200
    assert client.get("/cockpit/styles/knowledge_updates.css").status_code == 200
    assert client.get("/editor/").status_code == 200


def test_composed_shell_keeps_existing_api_boundary() -> None:
    client = TestClient(create_cockpit_app(connect_fn=_Connection, api_key="read-key"))

    assert client.get("/health").status_code == 200
    assert client.get("/v1/projects/project-a/documents").status_code == 401
    assert client.get("/v1/projects/project-a/work-issues").status_code == 401
    assert client.post(
        "/v1/projects/project-a/effects/preview",
        json={"information": "Préciser le choix de couverture."},
    ).status_code == 401


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


def test_effect_preview_route_is_authenticated_and_proposal_only(monkeypatch) -> None:
    observed = {}

    def preview(_conn, **values):
        observed.update(values)
        return {
            "parent_project_id": values["parent_project_id"],
            "status": "proposal_only",
            "matching_mode": "exact_project_then_deterministic_lexical",
            "information_digest": "sha256:fictional",
            "explicit_object_refs": values["explicit_object_refs"],
            "ambiguous": False,
            "proposals": [
                {
                    "proposal_id": "proposal-1",
                    "effect": "UPDATE",
                    "effect_source": "matched_object_default",
                    "target": {
                        "object_type": "knowledge",
                        "object_id": "knowledge.coverage",
                        "card_id": "card-knowledge.coverage",
                        "title": "Couverture zinc",
                        "current_status": "needs_review",
                    },
                    "candidate_object_type": "knowledge",
                    "score": 0.8,
                    "confidence": "high",
                    "reasons": ["Titre rapproché."],
                    "requires_human_confirmation": True,
                    "apply_route": None,
                }
            ],
            "limits": ["No proposal is persisted."],
        }

    monkeypatch.setattr(effect_preview, "preview_project_effects", preview)
    client = TestClient(create_cockpit_app(connect_fn=_Connection, api_key="read-key"))
    response = client.post(
        "/v1/projects/project-a/effects/preview",
        headers={"Authorization": "Bearer read-key"},
        json={
            "information": "Le client confirme la couverture zinc.",
            "explicit_object_refs": ["knowledge.coverage"],
            "effect_hint": "UPDATE",
            "max_proposals": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "proposal_only"
    assert payload["proposals"][0]["apply_route"] is None
    assert payload["proposals"][0]["requires_human_confirmation"] is True
    assert observed == {
        "parent_project_id": "project-a",
        "information": "Le client confirme la couverture zinc.",
        "explicit_object_refs": ["knowledge.coverage"],
        "effect_hint": "UPDATE",
        "max_proposals": 3,
    }
