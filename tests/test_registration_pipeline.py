"""Pipeline tests (M2) — one per FLUJO A edge case.

Few tests by design (methodology: no exhaustive suite yet). Run the whole
suite with ``uv run pytest`` or this file alone with
``uv run python tests/test_registration_pipeline.py``.

Uses in-memory fakes for the ports, so it never touches Supabase or Qwen.
"""

import asyncio
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

# Run directly (uv run python tests/...): put the repo root on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.domain.errors import DoseError, MissingFieldError, PlotNotFoundError
from app.core.domain.models import (
    Advisor,
    Equipment,
    Holding,
    Intervention,
    Plot,
    Product,
)
from app.core.domain.schemas import ExtractedFields
from app.core.services.registration_pipeline import RegistrationPipeline

ADV = UUID("11111111-1111-1111-1111-111111111111")
HOLD, PLOT, EQ = uuid4(), uuid4(), uuid4()
NOW = datetime(2026, 6, 15, 9, 0, tzinfo=timezone.utc)


class FakeTranscriber:
    async def transcribe(self, audio):
        return "texto dictado"


class FakeExtractor:
    prompt_version = "v1"

    def __init__(self, fields):
        self.fields = fields

    async def extract(self, transcription):
        return self.fields


class FakeRepo:
    def __init__(self):
        self.saved = None
        self.existing = None

    async def get_advisor(self, advisor_id):
        return Advisor(full_name="X", dni="1", ropo_number="R",
                       account_status="ACTIVE", id=ADV)

    async def get_intervention_by_transaction_id(self, transaction_id):
        return self.existing

    async def get_plot_by_alias(self, advisor_id, alias):
        if alias != "Finca de Pepe":
            return None
        return Plot(holding_id=HOLD, voice_alias=alias, crop="Limonero",
                    enclosure_area_ha=5.0, sigpac_province="30",
                    sigpac_municipality="001", sigpac_polygon="1",
                    sigpac_parcel="1", sigpac_enclosure="1", id=PLOT)

    async def get_product_by_name(self, name):
        return Product(registration_number="ES-1", trade_name=name,
                       active_substance="abamectina", authorized=True,
                       max_allowed_dose=1.5, dose_unit="L/ha",
                       pre_harvest_interval_days=14)

    async def get_equipment_by_alias(self, advisor_id, alias):
        return Equipment(holding_id=HOLD, equipment_alias=alias, id=EQ)

    async def get_holding(self, holding_id):
        return Holding(advisor_id=ADV, owner_name="Pepe", owner_nif="1",
                       rea_regepa_number="R", id=HOLD)

    async def save_intervention(self, iv):
        self.saved = replace(iv, id=uuid4())
        return self.saved


class FakePdf:
    def generate_prescription(self, **kwargs):
        return b"%PDF-fake"


class FakeStorage:
    async def upload(self, *, data, key, content_type):
        pass

    async def presigned_url(self, key, *, expires_seconds=3600):
        return f"https://fake/{key}"


async def _run(fields, repo=None):
    repo = repo or FakeRepo()
    pipeline = RegistrationPipeline(
        FakeTranscriber(), FakeExtractor(fields), repo, FakePdf(), FakeStorage()
    )
    iv = await pipeline.register(
        audio=b"x", advisor_id=ADV, transaction_id=uuid4(), device_timestamp=NOW
    )
    return iv, repo


async def main():
    iv, _ = await _run(ExtractedFields(
        record_type="OBSERVATION", plot_alias="Finca de Pepe", observation="3 capturas"))
    assert iv.lifecycle_state == "OBSERVATION"
    assert iv.observation == "3 capturas"
    assert iv.product_registration_number is None
    print("1 OBSERVATION ok")

    iv, _ = await _run(ExtractedFields(
        record_type="PRESCRIPTION", plot_alias="Finca de Pepe", product_name="Abamectina",
        dose=1.5, dose_unit="L/ha", target_pest="araña roja", equipment_alias="tractor"))
    assert iv.lifecycle_state == "PRESCRIBED"
    assert iv.prescribed_dose == 1.5 and iv.equipment_id == EQ and iv.audit_state == "VALID"
    assert iv.prescription_pdf_key is not None  # PDF rendered + stored (M3)
    print("2 PRESCRIPTION ok")

    iv, _ = await _run(ExtractedFields(
        record_type="EXECUTION", plot_alias="Finca de Pepe", product_name="Abamectina",
        dose=1.0, dose_unit="L/ha", target_pest="trips", equipment_alias="tractor",
        treated_area_ha=2.0))
    assert iv.lifecycle_state == "EXECUTED"
    assert str(iv.earliest_harvest_date) == "2026-06-29"  # NOW + PHI(14)
    assert iv.treatment_date == NOW
    print("3 EXECUTION + PHI ok")

    try:
        await _run(ExtractedFields(
            record_type="PRESCRIPTION", plot_alias="Finca de Pepe", product_name="Abamectina",
            dose=1.6, dose_unit="L/ha", target_pest="x", equipment_alias="tractor"))
        raise AssertionError("expected DoseError")
    except DoseError:
        print("4 DoseError ok")

    try:
        await _run(ExtractedFields(
            record_type="PRESCRIPTION", plot_alias="Finca de Pepe", product_name="Abamectina",
            dose=1.0, dose_unit="L/ha", target_pest="x"))
        raise AssertionError("expected MissingFieldError")
    except MissingFieldError:
        print("5 MissingFieldError ok")

    try:
        await _run(ExtractedFields(record_type="OBSERVATION", plot_alias="Finca Fantasma"))
        raise AssertionError("expected PlotNotFoundError")
    except PlotNotFoundError:
        print("6 PlotNotFoundError ok")

    repo = FakeRepo()
    repo.existing = Intervention(transaction_id=uuid4(), lifecycle_state="PRESCRIBED",
                                 advisor_id=ADV, holding_id=HOLD, plot_id=PLOT, id=uuid4())
    iv, repo = await _run(ExtractedFields(record_type="OBSERVATION", plot_alias="Finca de Pepe"), repo)
    assert iv is repo.existing and repo.saved is None  # idempotent: no insert
    print("7 Idempotency ok")

    print("ALL PIPELINE TESTS PASSED")


def test_registration_pipeline():
    """pytest entry point; the async body lives in main()."""
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
