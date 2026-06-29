"""Inbound HTTP auth: verify the Supabase JWT and resolve the advisor (M4).

The PWA logs in with a Supabase email OTP code (or password) and sends the
resulting access token as ``Authorization: Bearer <jwt>``. Supabase signs it with an asymmetric key
(ES256), so we verify the signature against the project's PUBLIC keys, published
at the JWKS endpoint — never the legacy shared HS256 secret (CLAUDE.md). No
secret lives here: verification uses public keys only.

The token's ``sub`` claim is the Supabase ``auth.users`` id; an advisor row links
to it through ``advisors.auth_user_id``. A valid token whose user is not an
advisor is rejected (401) — being authenticated is not being authorized.
"""

import asyncio
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import container
from app.config.settings import settings


class AuthError(Exception):
    """Authentication/authorization failure -> HTTP 401 at the API boundary."""


# Supabase publishes the signing key's public half at the JWKS endpoint;
# PyJWKClient fetches and caches it, refetching only on an unknown ``kid`` (key
# rotation). Built once at import — no network call until the first verify.
_ISSUER = f"{settings.supabase_url.rstrip('/')}/auth/v1"
_jwks_client = PyJWKClient(f"{_ISSUER}/.well-known/jwks.json")

# auto_error=False: a missing/badly-formed header yields None instead of FastAPI's
# own 403, so every auth failure flows through AuthError -> our 401 shape.
_bearer = HTTPBearer(auto_error=False)


def _verify(token: str) -> dict:
    """Verify signature + standard claims; return the token payload.

    Synchronous (PyJWT plus a possible JWKS HTTP fetch), so callers run it off
    the event loop. Raises on any failure (bad signature, expiry, wrong aud/iss).
    """
    signing_key = _jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256"],
        audience=settings.supabase_jwt_aud,
        issuer=_ISSUER,
        options={"require": ["exp", "sub"]},
    )


async def current_advisor_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UUID:
    """FastAPI dependency: a verified Bearer token -> the caller's advisor id.

    Replaces the M2 ``default_advisor_id`` stand-in — every record is now
    attributed to the authenticated advisor.
    """
    if credentials is None:
        raise AuthError("Falta el token de autenticación.")
    try:
        # JWKS fetch + verify is blocking I/O -> keep it off the event loop.
        claims = await asyncio.to_thread(_verify, credentials.credentials)
    except Exception as exc:  # any PyJWT error collapses into one 401
        raise AuthError("Token inválido o caducado.") from exc

    advisor = await container.repository.get_advisor_by_auth_user_id(
        UUID(claims["sub"])
    )
    if advisor is None:
        raise AuthError("La cuenta no está asociada a ningún asesor.")
    return advisor.id
