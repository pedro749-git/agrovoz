"""Generate a sample campaign-validation PDF to eyeball the template (M7).

No env/DB/OSS needed. Writes ``sample_validation.pdf`` to the repo root.

    uv run python tests/generate_sample_validation.py
"""

import sys
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.adapters.outbound.reportlab_pdf import ReportLabPdfGenerator
from app.core.domain.models import Advisor, Holding, Validation, ValidationType

advisor = Advisor(full_name="Pedro Flores Navarro", dni="12345678Z",
                  ropo_number="ROPO-AS-30-0001", account_status="ACTIVE", id=uuid4())
holding = Holding(advisor_id=advisor.id, owner_name="Pepe García",
                  owner_nif="87654321X", rea_regepa_number="REA-30-12345", id=uuid4())
validation = Validation(
    advisor_id=advisor.id, holding_id=holding.id, campaign="2026",
    type=ValidationType.FINAL,
    validation_date=datetime(2026, 11, 30, 12, 0, tzinfo=timezone.utc),
    conformity=False, period_start=date(2026, 1, 1), period_end=date(2026, 11, 30),
    intervention_count=14,
    remarks="Dos aplicaciones sin justificante de compra; regularizadas en campaña.",
)

pdf = ReportLabPdfGenerator().generate_validation(
    validation=validation, advisor=advisor, holding=holding,
)
assert pdf.startswith(b"%PDF"), "output is not a PDF"

out = Path(__file__).resolve().parents[1] / "sample_validation.pdf"
out.write_bytes(pdf)
print(f"OK · {len(pdf)} bytes -> {out}")
