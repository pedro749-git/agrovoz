"""Inbound API tests (M4): endpoint wiring + error -> HTTP mapping.

TestClient with the auth dependency overridden and a fake pipeline/repository,
so nothing touches Qwen/Supabase/OSS. Run: uv run pytest tests/test_api.py
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.adapters.inbound import api
from app.adapters.inbound.auth import current_advisor_id
from app.config import container
from app.core.domain.errors import DoseError, PlotNotFoundError, TranscriptionError
from app.core.domain.models import Intervention
from app.core.domain.states import LifecycleState

ADV = uuid4()


def _intervention(state=LifecycleState.PRESCRIBED):
    return Intervention(
        transaction_id=uuid4(), lifecycle_state=state, advisor_id=ADV,
        holding_id=uuid4(), plot_id=uuid4(), id=uuid4(),
        product_registration_number="ES-1", prescribed_dose=1.5,
        dose_unit="L/ha", target_pest="araña roja")


class FakePipeline:
    """Stands in for container.pipeline: returns a record or raises."""

    def __init__(self, result=None, error=None):
        self._result, self._error = result, error

    async def register(self, **kwargs):
        if self._error:
            raise self._error
        return self._result


@pytest.fixture
def client():
    """TestClient with auth bypassed (advisor = ADV). raise_server_exceptions is
    off so the catch-all 500 handler returns a response we can assert."""
    api.app.dependency_overrides[current_advisor_id] = lambda: ADV
    yield TestClient(api.app, raise_server_exceptions=False)
    api.app.dependency_overrides.clear()


def _post(client):
    return client.post(
        "/api/records",
        files={"audio": ("a.ogg", b"x", "audio/ogg")},
        data={"transaction_id": str(uuid4()),
              "device_timestamp": "2026-06-19T10:00:00Z"})


def test_post_record_200(client, monkeypatch):
    monkeypatch.setattr(container, "pipeline", FakePipeline(result=_intervention()))
    r = _post(client)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lifecycle_state"] == "PRESCRIBED"
    assert body["has_pdf"] is False and body["pdf_url"] is None


def test_domain_error_maps_to_422(client, monkeypatch):
    monkeypatch.setattr(container, "pipeline", FakePipeline(error=DoseError("dosis alta")))
    r = _post(client)
    assert r.status_code == 422 and r.json()["error"] == "DOSE_ERROR"


def test_not_found_error_maps_to_404(client, monkeypatch):
    monkeypatch.setattr(container, "pipeline", FakePipeline(error=PlotNotFoundError("no")))
    r = _post(client)
    assert r.status_code == 404 and r.json()["error"] == "PLOT_NOT_FOUND"


def test_infrastructure_error_maps_to_503(client, monkeypatch):
    monkeypatch.setattr(container, "pipeline", FakePipeline(error=TranscriptionError("qwen")))
    r = _post(client)
    assert r.status_code == 503 and r.json()["error"] == "INFRASTRUCTURE_ERROR"


def test_unexpected_error_maps_to_500(client, monkeypatch):
    monkeypatch.setattr(container, "pipeline", FakePipeline(error=ValueError("boom")))
    r = _post(client)
    assert r.status_code == 500 and r.json()["error"] == "INTERNAL_ERROR"


def test_list_interventions_200(client, monkeypatch):
    async def fake_list(advisor_id, *, state=None):
        assert advisor_id == ADV
        return [_intervention(), _intervention(LifecycleState.EXECUTED)]
    monkeypatch.setattr(container.repository, "list_interventions", fake_list)
    r = client.get("/api/interventions")
    assert r.status_code == 200 and len(r.json()) == 2


def test_post_without_token_401():
    # No dependency override -> the real auth dependency runs; no token -> 401.
    client = TestClient(api.app, raise_server_exceptions=False)
    r = _post(client)
    assert r.status_code == 401 and r.json()["error"] == "AUTH_ERROR"
