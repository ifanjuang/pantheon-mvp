"""Cards-first cockpit composition over the bounded Document/Knowledge API.

The shell exposes projections only. It does not own object status, approval,
execution, evidence, memory promotion or external action.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import store
from .cockpit_api import create_app

COCKPIT = Path(__file__).resolve().parent / "cockpit"


def create_cockpit_app(
    *,
    connect_fn: Callable = store.connect,
    document_root: str | Path | None = None,
    api_key: str | None = None,
    editor_api_key: str | None = None,
    hermes_api_key: str | None = None,
    public_url: str | None = None,
) -> FastAPI:
    """Compose the existing bounded API with the cards-first static shell."""
    app = create_app(
        connect_fn=connect_fn,
        document_root=document_root,
        api_key=api_key,
        editor_api_key=editor_api_key,
        hermes_api_key=hermes_api_key,
        public_url=public_url,
    )
    if COCKPIT.is_dir():
        app.mount("/cockpit", StaticFiles(directory=COCKPIT, html=True), name="cockpit")
    return app


app = create_cockpit_app()


def run() -> None:
    """Run the composed internal cockpit API with uvicorn."""
    import uvicorn

    uvicorn.run(
        "mvp_vertical.cockpit_shell:app",
        host=os.getenv("MVP_COCKPIT_HOST", "127.0.0.1"),
        port=int(os.getenv("MVP_COCKPIT_PORT", "8081")),
        reload=False,
    )


if __name__ == "__main__":
    run()
