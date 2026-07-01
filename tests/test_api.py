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
from app.core.domain.models import Equipment, Holding, Intervention, Plot
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


def test_get_intervention_detail_200(client, monkeypatch):
    iv = _intervention(LifecycleState.EXECUTED)
    iv.equipment_id = uuid4()
    iv.raw_transcription = "Finca de Pepe, abamectina, araña roja, tractor"
    iv.justification = "Superación de umbral"

    async def fake_get(intervention_id, advisor_id):
        assert intervention_id == iv.id and advisor_id == ADV
        return iv

    async def fake_plot(plot_id):
        return Plot(
            holding_id=iv.holding_id, voice_alias="Finca de Pepe", crop="Limonero",
            variety="Fino", enclosure_area_ha=3.5, sigpac_province="30",
            sigpac_municipality="015", sigpac_polygon="012", sigpac_parcel="00045",
            sigpac_enclosure="003", id=iv.plot_id)

    async def fake_holding(holding_id):
        return Holding(advisor_id=ADV, owner_name="José Ruiz", owner_nif="1",
                       rea_regepa_number="REA-30-00123", id=iv.holding_id)

    async def fake_equipment(equipment_id):
        return Equipment(holding_id=iv.holding_id, equipment_alias="tractor",
                         roma_number="ROMA-30-00077", id=equipment_id)

    monkeypatch.setattr(container.repository, "get_intervention", fake_get)
    monkeypatch.setattr(container.repository, "get_plot", fake_plot)
    monkeypatch.setattr(container.repository, "get_holding", fake_holding)
    monkeypatch.setattr(container.repository, "get_equipment", fake_equipment)

    r = client.get(f"/api/interventions/{iv.id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["raw_transcription"].startswith("Finca de Pepe")
    assert body["justification"] == "Superación de umbral"
    assert body["plot"]["crop"] == "Limonero"
    assert body["plot"]["sigpac"] == "30:015:012:00045:003"
    assert body["holding"]["owner_name"] == "José Ruiz"
    assert body["equipment"]["equipment_alias"] == "tractor"


def test_get_intervention_detail_404(client, monkeypatch):
    async def fake_get(intervention_id, advisor_id):
        return None  # not yours / does not exist -> indistinguishable 404

    monkeypatch.setattr(container.repository, "get_intervention", fake_get)
    r = client.get(f"/api/interventions/{uuid4()}")
    assert r.status_code == 404 and r.json()["error"] == "INTERVENTION_NOT_FOUND"


def test_get_pdf_200(client, monkeypatch):
    iv = _intervention()
    iv.prescription_pdf_key = "prescriptions/x.pdf"

    async def fake_get(intervention_id, advisor_id):
        assert intervention_id == iv.id and advisor_id == ADV
        return iv

    async def fake_exists(key):
        assert key == "prescriptions/x.pdf"
        return True

    async def fake_sign(key):
        assert key == "prescriptions/x.pdf"
        return "https://oss/signed"

    monkeypatch.setattr(container.repository, "get_intervention", fake_get)
    monkeypatch.setattr(container.storage, "exists", fake_exists)
    monkeypatch.setattr(container.storage, "presigned_url", fake_sign)
    r = client.get(f"/api/interventions/{iv.id}/pdf")
    assert r.status_code == 200 and r.json()["pdf_url"] == "https://oss/signed"


def test_get_pdf_404_when_object_missing(client, monkeypatch):
    iv = _intervention()
    iv.prescription_pdf_key = "prescriptions/gone.pdf"  # key in DB, object gone

    async def fake_get(intervention_id, advisor_id):
        return iv

    async def fake_exists(key):
        return False

    monkeypatch.setattr(container.repository, "get_intervention", fake_get)
    monkeypatch.setattr(container.storage, "exists", fake_exists)
    r = client.get(f"/api/interventions/{iv.id}/pdf")
    assert r.status_code == 404 and r.json()["error"] == "PDF_NOT_FOUND"


def test_get_pdf_404_when_record_missing(client, monkeypatch):
    async def fake_get(intervention_id, advisor_id):
        return None  # not yours / does not exist -> indistinguishable 404

    monkeypatch.setattr(container.repository, "get_intervention", fake_get)
    r = client.get(f"/api/interventions/{uuid4()}/pdf")
    assert r.status_code == 404 and r.json()["error"] == "INTERVENTION_NOT_FOUND"


def test_get_pdf_404_when_no_pdf(client, monkeypatch):
    iv = _intervention()  # prescription_pdf_key is None (e.g. an OBSERVATION)

    async def fake_get(intervention_id, advisor_id):
        return iv

    monkeypatch.setattr(container.repository, "get_intervention", fake_get)
    r = client.get(f"/api/interventions/{iv.id}/pdf")
    assert r.status_code == 404 and r.json()["error"] == "PDF_NOT_FOUND"


def test_post_without_token_401():
    # No dependency override -> the real auth dependency runs; no token -> 401.
    client = TestClient(api.app, raise_server_exceptions=False)
    r = _post(client)
    assert r.status_code == 401 and r.json()["error"] == "AUTH_ERROR"
