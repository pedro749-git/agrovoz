"""ReportLab adapter smoke test (M7).

The service tests use a FakePdf, so the REAL validation render is otherwise
uncovered — a broken story would only surface at runtime. One smoke test that it
produces a PDF (and does not choke on optional/None fields) is enough here; the
prescription render is exercised via the pipeline test.
    uv run pytest tests/test_reportlab_pdf.py
"""

from datetime import date, datetime, timezone
from uuid import uuid4

from app.adapters.outbound.reportlab_pdf import ReportLabPdfGenerator
from app.core.domain.models import Advisor, Holding, Validation, ValidationType

ADV = uuid4()
HOLD = uuid4()


def _validation(**overrides) -> Validation:
    base = dict(
        advisor_id=ADV, holding_id=HOLD, campaign="2026",
        type=ValidationType.MID_CYCLE,
        validation_date=datetime(2026, 6, 30, 10, 0, tzinfo=timezone.utc),
        conformity=True, period_start=date(2026, 1, 1), period_end=date(2026, 6, 30),
        intervention_count=3, id=uuid4(),
    )
    base.update(overrides)
    return Validation(**base)


def test_generate_validation_returns_pdf_bytes():
    advisor = Advisor(full_name="Ana", dni="0T", ropo_number="R1", id=ADV)
    holding = Holding(advisor_id=ADV, owner_name="Pepe", owner_nif="1X",
                      rea_regepa_number="REA-1", id=HOLD)
    pdf = ReportLabPdfGenerator().generate_validation(
        validation=_validation(), advisor=advisor, holding=holding,
    )
    assert pdf.startswith(b"%PDF") and len(pdf) > 500


def test_generate_validation_handles_non_conform_without_remarks():
    # remarks=None (a conform doc, or data not yet filled) must render an em dash,
    # not crash — the adapter is untrusted-input tolerant.
    advisor = Advisor(full_name="Ana", dni="0T", ropo_number="R1", id=ADV)
    holding = Holding(advisor_id=ADV, owner_name="Pepe", owner_nif="1X",
                      rea_regepa_number="REA-1", id=HOLD)
    pdf = ReportLabPdfGenerator().generate_validation(
        validation=_validation(conformity=False, remarks=None),
        advisor=advisor, holding=holding,
    )
    assert pdf.startswith(b"%PDF")
