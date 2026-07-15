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
from app.core.domain.errors import (
    DoseError,
    HoldingNotFoundError,
    PlotNotFoundError,
    TranscriptionError,
    ValidationExistsError,
)
from app.core.domain.models import (
    Equipment,
    Holding,
    Intervention,
    Plot,
    Product,
    Validation,
    ValidationType,
)
from app.core.domain.states import LifecycleState

ADV = uuid4()


def _intervention(state=LifecycleState.PRESCRIBED):
    return Intervention(
        transaction_id=uuid4(), lifecycle_state=state, advisor_id=ADV,
        holding_id=uuid4(), plot_id=uuid4(), id=uuid4(),
        product_registration_number="ES-1", prescribed_dose=1.5,
        dose_unit="L/ha", target_pest="araña roja")


class FakePipeline:
    """Stands in for container.pipeline: returns a record/preview or raises."""

    def __init__(self, result=None, error=None, preview=None):
        self._result, self._error, self._preview = result, error, preview

    async def commit(self, **kwargs):
        if self._error:
            raise self._error
        return self._result

    async def preview(self, **kwargs):
        if self._error:
            raise self._error
        return self._preview


@pytest.fixture
def client():
    """TestClient with auth bypassed (advisor = ADV). raise_server_exceptions is
    off so the catch-all 500 handler returns a response we can assert."""
    api.app.dependency_overrides[current_advisor_id] = lambda: ADV
    yield TestClient(api.app, raise_server_exceptions=False)
    api.app.dependency_overrides.clear()


def _post(client):
    """POST the commit endpoint: reviewed fields as JSON (M8), not audio."""
    return client.post(
        "/api/records",
        json={"fields": {"record_type": "OBSERVATION", "plot_alias": "Finca de Pepe"},
              "transaction_id": str(uuid4()),
              "device_timestamp": "2026-06-19T10:00:00Z",
              "transcription": "texto dictado"})


def test_post_record_200(client, monkeypatch):
    monkeypatch.setattr(container, "pipeline", FakePipeline(result=_intervention()))
    r = _post(client)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lifecycle_state"] == "PRESCRIBED"
    assert body["has_pdf"] is False and body["pdf_url"] is None


def test_preview_record_200(client, monkeypatch):
    from app.core.domain.models import Product
    from app.core.domain.schemas import ExtractedFields
    from app.core.services.registration_pipeline import PreviewResult

    plot = Plot(
        holding_id=uuid4(), voice_alias="Finca de Pepe", crop="Limonero",
        enclosure_area_ha=3.5, sigpac_province="30", sigpac_municipality="015",
        sigpac_polygon="012", sigpac_parcel="00045", sigpac_enclosure="003", id=uuid4())
    product = Product(
        registration_number="ES-1", trade_name="Abamectina", active_substance="abamectina",
        authorized=True, max_allowed_dose=1.5, dose_unit="L/ha", pre_harvest_interval_days=14)
    preview = PreviewResult(
        transcription="Finca de Pepe, abamectina, araña roja, tractor",
        fields=ExtractedFields(
            record_type="PRESCRIPTION", plot_alias="Finca de Pepe",
            product_name="Abamectina", dose=1.5, dose_unit="L/ha",
            target_pest="araña roja", equipment_alias="tractor"),
        plot=plot, product=product, equipment=None)  # equipment unresolved -> flagged
    monkeypatch.setattr(container, "pipeline", FakePipeline(preview=preview))
    r = client.post("/api/records/preview",
                    files={"audio": ("a.ogg", b"x", "audio/ogg")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fields"]["product_name"] == "Abamectina"
    assert body["resolution"]["plot"] == {
        "found": True, "crop": "Limonero", "sigpac": "30:015:012:00045:003"}
    assert body["resolution"]["product"]["found"] is True
    assert body["resolution"]["equipment"]["found"] is False


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
    # The endpoint resolves the card names (trade name, plot alias, owner) in
    # three batch lookups; fake them with context for iv1 only, so iv2 also
    # proves the fallback (missing row -> null names, never an error).
    iv1, iv2 = _intervention(), _intervention(LifecycleState.EXECUTED)

    async def fake_list(advisor_id, *, state=None, since=None, until=None):
        assert advisor_id == ADV
        return [iv1, iv2]

    async def fake_plots(plot_ids):
        return [Plot(
            holding_id=iv1.holding_id, voice_alias="Finca de Pepe",
            crop="Limonero", enclosure_area_ha=3.5, sigpac_province="30",
            sigpac_municipality="015", sigpac_polygon="012",
            sigpac_parcel="00045", sigpac_enclosure="003", id=iv1.plot_id)]

    async def fake_holdings(holding_ids):
        return [Holding(advisor_id=ADV, owner_name="José Ruiz", owner_nif="1",
                        rea_regepa_number="REA-30-00123", id=iv1.holding_id)]

    async def fake_products(registration_numbers):
        return [Product(registration_number="ES-1", trade_name="Abamectina",
                        active_substance="abamectina")]

    monkeypatch.setattr(container.repository, "list_interventions", fake_list)
    monkeypatch.setattr(container.repository, "list_plots_by_ids", fake_plots)
    monkeypatch.setattr(container.repository, "list_holdings_by_ids", fake_holdings)
    monkeypatch.setattr(
        container.repository, "list_products_by_registration_numbers", fake_products
    )
    r = client.get("/api/interventions")
    assert r.status_code == 200 and len(r.json()) == 2
    first, second = r.json()
    assert first["product_trade_name"] == "Abamectina"
    assert first["plot_alias"] == "Finca de Pepe"
    assert first["holding_owner_name"] == "José Ruiz"
    # iv2's plot/holding were not in the batch results: names are null.
    assert second["plot_alias"] is None
    assert second["holding_owner_name"] is None


def test_list_interventions_date_range_maps_to_utc_window(client, monkeypatch):
    # ?from=&to= are civil Madrid days, inclusive. Summer (CEST = UTC+2), so the
    # window must be [from 00:00 → 22:00 UTC the day before, (to+1) 00:00 → 22:00
    # UTC on `to`), NOT a naive same-date comparison.
    from datetime import datetime, timezone

    captured = {}

    async def fake_list(advisor_id, *, state=None, since=None, until=None):
        captured["since"] = since
        captured["until"] = until
        return []

    monkeypatch.setattr(container.repository, "list_interventions", fake_list)
    r = client.get("/api/interventions?from=2026-07-06&to=2026-07-06")
    assert r.status_code == 200
    assert captured["since"] == datetime(2026, 7, 5, 22, 0, tzinfo=timezone.utc)
    assert captured["until"] == datetime(2026, 7, 6, 22, 0, tzinfo=timezone.utc)


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

    async def fake_product(registration_number):
        assert registration_number == "ES-1"
        return Product(registration_number="ES-1", trade_name="Abamectina",
                       active_substance="abamectina")

    monkeypatch.setattr(container.repository, "get_intervention", fake_get)
    monkeypatch.setattr(container.repository, "get_plot", fake_plot)
    monkeypatch.setattr(container.repository, "get_holding", fake_holding)
    monkeypatch.setattr(container.repository, "get_equipment", fake_equipment)
    monkeypatch.setattr(container.repository,
                        "get_product_by_registration_number", fake_product)

    r = client.get(f"/api/interventions/{iv.id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["raw_transcription"].startswith("Finca de Pepe")
    assert body["justification"] == "Superación de umbral"
    assert body["plot"]["crop"] == "Limonero"
    assert body["plot"]["sigpac"] == "30:015:012:00045:003"
    assert body["holding"]["owner_name"] == "José Ruiz"
    assert body["equipment"]["equipment_alias"] == "tractor"
    # The M8.2 product block: the trade name the detail shows and the
    # correction form prefills (the record itself stores only the MAPA number).
    assert body["product"]["trade_name"] == "Abamectina"


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


def test_assess_effectiveness_200(client, monkeypatch):
    iv = _intervention(LifecycleState.ASSESSED)
    captured = {}

    class FakeAssessment:
        async def assess(self, **kwargs):
            captured.update(kwargs)
            return iv

    monkeypatch.setattr(container, "assessment_service", FakeAssessment())
    r = client.patch(
        f"/api/interventions/{iv.id}/effectiveness",
        data={"effectiveness": "GOOD", "effectiveness_date": "2026-06-29",
              "effectiveness_notes": "La plaga remitió"})
    assert r.status_code == 200, r.text
    assert r.json()["lifecycle_state"] == "ASSESSED"
    # The enum and date are parsed at the boundary before reaching the service.
    assert captured["effectiveness"].value == "GOOD"
    assert str(captured["effectiveness_date"]) == "2026-06-29"


def test_assess_bad_effectiveness_422(client):
    # An out-of-enum value is rejected by FastAPI validation before the service.
    r = client.patch(
        f"/api/interventions/{uuid4()}/effectiveness",
        data={"effectiveness": "EXCELLENT", "effectiveness_date": "2026-06-29"})
    assert r.status_code == 422


def test_transcribe_200(client, monkeypatch):
    class FakeTranscriber:
        async def transcribe(self, audio):
            assert audio == b"x"
            return "la plaga ha remitido bastante"

    monkeypatch.setattr(container, "transcriber", FakeTranscriber())
    r = client.post("/api/transcribe",
                    files={"audio": ("a.ogg", b"x", "audio/ogg")})
    assert r.status_code == 200, r.text
    assert r.json()["text"] == "la plaga ha remitido bastante"


def _validation(**overrides):
    base = dict(
        advisor_id=ADV, holding_id=uuid4(), campaign="2026",
        type=ValidationType.MID_CYCLE,
        validation_date="2026-06-30T10:00:00Z", conformity=True,
        period_start="2026-01-01", period_end="2026-06-30",
        intervention_count=3, id=uuid4())
    base.update(overrides)
    from datetime import date, datetime
    base["validation_date"] = datetime.fromisoformat(base["validation_date"])
    base["period_start"] = date.fromisoformat(base["period_start"])
    base["period_end"] = date.fromisoformat(base["period_end"])
    return Validation(**base)


def test_create_validation_200(client, monkeypatch):
    holding_id = uuid4()
    val = _validation(holding_id=holding_id)
    captured = {}

    class FakeService:
        async def validate_campaign(self, **kwargs):
            captured.update(kwargs)
            return val

    monkeypatch.setattr(container, "campaign_validation_service", FakeService())
    r = client.post(
        f"/api/holdings/{holding_id}/validations",
        data={"campaign": "2026", "validation_type": "MID_CYCLE",
              "conformity": "true", "validation_date": "2026-06-30T10:00:00Z"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["type"] == "MID_CYCLE"
    assert body["intervention_count"] == 3
    # No PDF key on the returned validation -> no link, no OSS call.
    assert body["pdf_url"] is None
    # The enum is parsed at the boundary before reaching the service.
    assert captured["validation_type"].value == "MID_CYCLE"


def test_create_validation_signs_pdf_url_when_key_present(client, monkeypatch):
    # A validation saved with a PDF key -> the response carries a presigned link.
    val = _validation(validation_pdf_key="validations/x.pdf")

    class FakeService:
        async def validate_campaign(self, **kwargs):
            return val

    async def fake_sign(key):
        assert key == "validations/x.pdf"
        return "https://oss.example/signed"

    monkeypatch.setattr(container, "campaign_validation_service", FakeService())
    monkeypatch.setattr(container.storage, "presigned_url", fake_sign)
    r = client.post(
        f"/api/holdings/{uuid4()}/validations",
        data={"campaign": "2026", "validation_type": "FINAL",
              "conformity": "true", "validation_date": "2026-06-30T10:00:00Z"})
    assert r.status_code == 200, r.text
    assert r.json()["pdf_url"] == "https://oss.example/signed"


def test_create_validation_bad_type_422(client):
    # An out-of-enum type is rejected by FastAPI validation before the service.
    r = client.post(
        f"/api/holdings/{uuid4()}/validations",
        data={"campaign": "2026", "validation_type": "YEARLY",
              "conformity": "true", "validation_date": "2026-06-30T10:00:00Z"})
    assert r.status_code == 422


def test_create_validation_duplicate_422(client, monkeypatch):
    class FakeService:
        async def validate_campaign(self, **kwargs):
            raise ValidationExistsError("ya existe")

    monkeypatch.setattr(container, "campaign_validation_service", FakeService())
    r = client.post(
        f"/api/holdings/{uuid4()}/validations",
        data={"campaign": "2026", "validation_type": "FINAL",
              "conformity": "true", "validation_date": "2026-06-30T10:00:00Z"})
    assert r.status_code == 422 and r.json()["error"] == "VALIDATION_EXISTS"


def test_create_validation_foreign_holding_404(client, monkeypatch):
    class FakeService:
        async def validate_campaign(self, **kwargs):
            raise HoldingNotFoundError("no encuentro esa explotación")

    monkeypatch.setattr(container, "campaign_validation_service", FakeService())
    r = client.post(
        f"/api/holdings/{uuid4()}/validations",
        data={"campaign": "2026", "validation_type": "FINAL",
              "conformity": "true", "validation_date": "2026-06-30T10:00:00Z"})
    assert r.status_code == 404 and r.json()["error"] == "HOLDING_NOT_FOUND"


def test_list_holdings_200(client, monkeypatch):
    holding = Holding(advisor_id=ADV, owner_name="Pepe García", owner_nif="1X",
                      rea_regepa_number="REA-1", id=uuid4())
    plot = Plot(holding_id=holding.id, voice_alias="Finca de Pepe", crop="Limonero",
                enclosure_area_ha=3.5, sigpac_province="30", sigpac_municipality="1",
                sigpac_polygon="1", sigpac_parcel="1", sigpac_enclosure="1", id=uuid4())
    val = _validation(holding_id=holding.id)

    async def fake_holdings(advisor_id):
        assert advisor_id == ADV
        return [holding]

    async def fake_plots(holding_id):
        assert holding_id == holding.id
        return [plot]

    async def fake_validations(holding_id, campaign=None):
        assert holding_id == holding.id and campaign is None  # all campaigns
        return [val]

    monkeypatch.setattr(container.repository, "list_holdings", fake_holdings)
    monkeypatch.setattr(container.repository, "list_plots", fake_plots)
    monkeypatch.setattr(container.repository, "list_validations", fake_validations)
    r = client.get("/api/holdings")
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body) == 1
    assert body[0]["owner_name"] == "Pepe García"
    assert body[0]["plots"] == [{"voice_alias": "Finca de Pepe", "crop": "Limonero"}]
    assert body[0]["validations"][0]["type"] == "MID_CYCLE"


def test_get_validation_pdf_200(client, monkeypatch):
    val = _validation(validation_pdf_key="validations/x.pdf")

    async def fake_get(validation_id, advisor_id):
        assert validation_id == val.id and advisor_id == ADV
        return val

    async def fake_exists(key):
        return True

    async def fake_sign(key):
        assert key == "validations/x.pdf"
        return "https://oss/signed-val"

    monkeypatch.setattr(container.repository, "get_validation", fake_get)
    monkeypatch.setattr(container.storage, "exists", fake_exists)
    monkeypatch.setattr(container.storage, "presigned_url", fake_sign)
    r = client.get(f"/api/validations/{val.id}/pdf")
    assert r.status_code == 200 and r.json()["pdf_url"] == "https://oss/signed-val"


def test_get_validation_pdf_404_when_no_key(client, monkeypatch):
    val = _validation()  # saved without a PDF (best-effort render/upload failed)

    async def fake_get(validation_id, advisor_id):
        return val

    monkeypatch.setattr(container.repository, "get_validation", fake_get)
    r = client.get(f"/api/validations/{val.id}/pdf")
    assert r.status_code == 404 and r.json()["error"] == "PDF_NOT_FOUND"


def test_get_validation_pdf_404_when_foreign(client, monkeypatch):
    async def fake_get(validation_id, advisor_id):
        return None  # not yours / does not exist -> indistinguishable 404

    monkeypatch.setattr(container.repository, "get_validation", fake_get)
    r = client.get(f"/api/validations/{uuid4()}/pdf")
    assert r.status_code == 404 and r.json()["error"] == "VALIDATION_NOT_FOUND"


def test_post_without_token_401():
    # No dependency override -> the real auth dependency runs; no token -> 401.
    client = TestClient(api.app, raise_server_exceptions=False)
    r = _post(client)
    assert r.status_code == 401 and r.json()["error"] == "AUTH_ERROR"
