#!/usr/bin/env python3
"""Deterministic local services for the Hermes 0.20.0 laboratory acceptance.

This fixture is test infrastructure only. It provides:

- a local OpenAI-compatible chat endpoint that deterministically requests the
  two Pantheon context tools;
- a bounded fake Pantheon execution API for one synthetic read-only admission;
- a sanitized request journal used to prove which surfaces were exercised.

It stores no credentials and never calls an external service.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

ADMISSION_ID = "admission-hermes-020-lab"
PANTHEON_KEY = "pantheon-lab-key"
PROFILE_ENTITY_TYPE = "project"
PROFILE_ENTITY_ID = "project-lab"
OUTSIDE_ENTITY_ID = "project-outside"


class LabState:
    def __init__(self, journal: Path) -> None:
        self.journal = journal
        self.lock = threading.Lock()
        self.provider_calls = 0
        self.pantheon_reads: list[str] = []
        self.pantheon_writes: list[str] = []

    def record(self, payload: dict[str, Any]) -> None:
        payload = {"recorded_at": time.time(), **payload}
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        with self.lock:
            self.journal.parent.mkdir(parents=True, exist_ok=True)
            with self.journal.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "provider_calls": self.provider_calls,
                "pantheon_reads": list(self.pantheon_reads),
                "pantheon_writes": list(self.pantheon_writes),
            }


class Handler(BaseHTTPRequestHandler):
    server_version = "PantheonHermesLab/1"

    @property
    def state(self) -> LabState:
        return self.server.lab_state  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: object) -> None:
        del fmt, args

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("request body must be an object")
        return value

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _journal(self, *, body: dict[str, Any] | None = None) -> None:
        self.state.record(
            {
                "method": self.command,
                "path": urlsplit(self.path).path,
                "authorization_present": bool(self.headers.get("Authorization")),
                "session_memory_header_present": bool(
                    self.headers.get("X-Hermes-Session-Key")
                ),
                "pantheon_actor": self.headers.get("X-Pantheon-Hermes-Actor"),
                "body_keys": sorted(body) if isinstance(body, dict) else [],
            }
        )

    def _pantheon_auth_ok(self) -> bool:
        return self.headers.get("Authorization") == f"Bearer {PANTHEON_KEY}"

    def do_GET(self) -> None:  # noqa: N802
        path = unquote(urlsplit(self.path).path)
        self._journal()

        if path == "/health":
            self._send(HTTPStatus.OK, {"status": "ok"})
            return
        if path == "/v1/models":
            self._send(
                HTTPStatus.OK,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": "lab-model",
                            "object": "model",
                            "owned_by": "pantheon-lab",
                        }
                    ],
                },
            )
            return
        if path == "/_lab/state":
            self._send(HTTPStatus.OK, self.state.snapshot())
            return

        prefix = f"/hermes/execution-admissions/{ADMISSION_ID}/active-context"
        if path.startswith(prefix):
            if not self._pantheon_auth_ok():
                self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            with self.state.lock:
                self.state.pantheon_reads.append(path)
            if path == prefix:
                self._send(
                    HTTPStatus.OK,
                    {
                        "kind": "active_context_manifest",
                        "admission_id": ADMISSION_ID,
                        "entities": [
                            {
                                "entity_type": PROFILE_ENTITY_TYPE,
                                "entity_id": PROFILE_ENTITY_ID,
                                "digest": "sha256:" + "1" * 64,
                            }
                        ],
                        "technical_fixture": True,
                        "evidence_admitted": False,
                    },
                )
                return
            entity_prefix = prefix + "/entities/"
            if path == entity_prefix + f"{PROFILE_ENTITY_TYPE}/{PROFILE_ENTITY_ID}":
                self._send(
                    HTTPStatus.OK,
                    {
                        "entity_type": PROFILE_ENTITY_TYPE,
                        "entity_id": PROFILE_ENTITY_ID,
                        "payload": {"name": "Hermes 0.20 laboratory project"},
                        "source": "synthetic_lab_fixture",
                        "evidence_admitted": False,
                    },
                )
                return
            if path == entity_prefix + f"{PROFILE_ENTITY_TYPE}/{OUTSIDE_ENTITY_ID}":
                self._send(
                    HTTPStatus.NOT_FOUND,
                    {"error": "entity is outside the admitted Context Pack"},
                )
                return

        self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = unquote(urlsplit(self.path).path)
        try:
            body = self._read_json()
        except Exception as exc:
            self._journal()
            self._send(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self._journal(body=body)

        if path == "/v1/chat/completions":
            self._handle_chat(body)
            return

        if path.startswith(f"/hermes/execution-admissions/{ADMISSION_ID}/"):
            if not self._pantheon_auth_ok():
                self._send(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            with self.state.lock:
                self.state.pantheon_writes.append(path)
            if path.endswith("/launch-reservations"):
                self._send(
                    HTTPStatus.CREATED,
                    {
                        "launch_reservation_id": "launch-reservation-hermes-020-lab",
                        "snapshot_id": "launch-snapshot-hermes-020-lab",
                        "snapshot_digest": "sha256:" + "2" * 64,
                        "work_issue_version": 1,
                        "replayed": False,
                        "snapshot": {
                            "kind": "hermes_launch_context_snapshot",
                            "question": "Read the admitted manifest and project, then verify that an outside project is refused.",
                            "field_projection_version": "hermes-020-lab",
                            "entities": [
                                {
                                    "entity_type": PROFILE_ENTITY_TYPE,
                                    "entity_id": PROFILE_ENTITY_ID,
                                }
                            ],
                        },
                    },
                )
                return
            if path.endswith("/runs/start"):
                self._send(
                    HTTPStatus.CREATED,
                    {
                        "runtime_start_recorded": True,
                        "work_issue": {"version": 2},
                        "task_authorized": False,
                        "evidence_admitted": False,
                    },
                )
                return
            if "/runs/" in path and path.endswith("/return"):
                self._send(
                    HTTPStatus.CREATED,
                    {
                        "runtime_return_recorded": True,
                        "work_issue": {"version": 3},
                        "result_accepted": False,
                        "evidence_admitted": False,
                        "project_mutated": False,
                    },
                )
                return

        self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _handle_chat(self, body: dict[str, Any]) -> None:
        messages = body.get("messages")
        if not isinstance(messages, list):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "messages required"})
            return
        tools = body.get("tools") or []
        available = {
            str(item.get("function", {}).get("name") or "")
            for item in tools
            if isinstance(item, dict)
        }
        required = {"pantheon_context_manifest", "pantheon_context_entity"}
        if not required.issubset(available):
            self._send(
                HTTPStatus.BAD_REQUEST,
                {"error": "expected Pantheon context tools are not available"},
            )
            return

        tool_messages = [
            item for item in messages if isinstance(item, dict) and item.get("role") == "tool"
        ]
        step = len(tool_messages)
        with self.state.lock:
            self.state.provider_calls += 1

        if step == 0:
            name = "pantheon_context_manifest"
            arguments = "{}"
        elif step == 1:
            name = "pantheon_context_entity"
            arguments = json.dumps(
                {"entity_type": PROFILE_ENTITY_TYPE, "entity_id": PROFILE_ENTITY_ID}
            )
        elif step == 2:
            name = "pantheon_context_entity"
            arguments = json.dumps(
                {"entity_type": PROFILE_ENTITY_TYPE, "entity_id": OUTSIDE_ENTITY_ID}
            )
        else:
            admitted = tool_messages[1].get("content", "") if len(tool_messages) > 1 else ""
            refused = tool_messages[2].get("content", "") if len(tool_messages) > 2 else ""
            if PROFILE_ENTITY_ID not in str(admitted):
                self._send(HTTPStatus.BAD_REQUEST, {"error": "admitted entity was not returned"})
                return
            if "HTTP 404" not in str(refused) and "outside" not in str(refused):
                self._send(HTTPStatus.BAD_REQUEST, {"error": "outside entity was not refused"})
                return
            self._send(
                HTTPStatus.OK,
                {
                    "id": "chatcmpl-hermes-020-lab-final",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": "lab-model",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": "LAB_ACCEPTANCE_COMPLETED: manifest read, admitted entity read, outside entity refused.",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 10,
                        "total_tokens": 20,
                    },
                },
            )
            return

        self._send(
            HTTPStatus.OK,
            {
                "id": f"chatcmpl-hermes-020-lab-{step}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "lab-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": f"call-hermes-020-lab-{step}",
                                    "type": "function",
                                    "function": {
                                        "name": name,
                                        "arguments": arguments,
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            },
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9010)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args()

    state = LabState(args.journal)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.lab_state = state  # type: ignore[attr-defined]
    print(f"Hermes 0.20 lab fixture listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
