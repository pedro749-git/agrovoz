"""Auth dependency tests (M4): a verified token -> advisor id (happy + 401s).

Mocks _verify (no real JWKS/network) and the repository lookup, so it stays a
pure unit. Run: uv run pytest tests/test_auth.py
"""

import asyncio
from uuid import uuid4

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.adapters.inbound import auth
from app.config import container
from app.core.domain.models import Advisor


def _creds(token="tok"):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def _advisor(advisor_id):
    return Advisor(full_name="Pedro", dni="1", ropo_number="R",
                   account_status="ACTIVE", id=advisor_id)


def _lookup_returning(advisor):
    async def lookup(auth_user_id):
        return advisor
    return lookup


def test_valid_token_resolves_advisor(monkeypatch):
    advisor_id, user_id = uuid4(), uuid4()
    monkeypatch.setattr(auth, "_verify", lambda token: {"sub": str(user_id), "exp": 1})
    monkeypatch.setattr(container.repository, "get_advisor_by_auth_user_id",
                        _lookup_returning(_advisor(advisor_id)))
    assert asyncio.run(auth.current_advisor_id(_creds())) == advisor_id


def test_missing_token_raises():
    with pytest.raises(auth.AuthError):
        asyncio.run(auth.current_advisor_id(None))


def test_invalid_token_raises(monkeypatch):
    def boom(token):
        raise ValueError("bad signature")
    monkeypatch.setattr(auth, "_verify", boom)
    with pytest.raises(auth.AuthError):
        asyncio.run(auth.current_advisor_id(_creds("garbage")))


def test_authenticated_but_not_advisor_raises(monkeypatch):
    # Valid token whose user is not provisioned as an advisor -> 401 (authn != authz).
    monkeypatch.setattr(auth, "_verify", lambda token: {"sub": str(uuid4()), "exp": 1})
    monkeypatch.setattr(container.repository, "get_advisor_by_auth_user_id",
                        _lookup_returning(None))
    with pytest.raises(auth.AuthError):
        asyncio.run(auth.current_advisor_id(_creds()))
