"""FastAPI application factory.

Keeps app construction in one place so tests can build a fresh app and the ASGI
server (uvicorn) can import ``app.main:app``.
"""
from __future__ import annotations

from fastapi import FastAPI

from . import __version__
from .api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Revenue Quality Scoring Service",
        version=__version__,
        description=(
            "Ingest a bank-statement CSV and assess how trustworthy the borrower's "
            "reported revenue is: inflow breakdown, pattern anomalies, a 0-100 "
            "revenue quality score and a lending recommendation."
        ),
    )
    app.include_router(router)
    return app


app = create_app()
