"""API-key authentication.

A single shared key is read from the environment (``RQS_API_KEY``) and required
on every protected route via the ``X-API-Key`` header. Comparison is
constant-time to avoid leaking the key through timing. This is deliberately
simple — appropriate for a service-to-service internal API; for multi-tenant use
you would swap this for per-client keys or OAuth without touching the routes.
"""
from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from ..config import Settings, get_settings

# auto_error=False so we can return our own JSON error shape instead of FastAPI's.
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(
    provided: str | None = Depends(_api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    """FastAPI dependency that rejects requests without a valid API key."""
    expected = settings.api_key
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key. Send it in the X-API-Key header.",
            headers={"WWW-Authenticate": "API-Key"},
        )
