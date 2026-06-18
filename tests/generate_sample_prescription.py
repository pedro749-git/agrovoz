"""Generate a sample prescription PDF to eyeball the template (M3, step 1).

No env/DB/OSS needed. Writes ``sample_prescription.pdf`` to the repo root.

    uv run python tests/generate_sample_prescription.py
"""

import sys
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.adapters.outbound.reportlab_pdf import ReportLabPdfGenerator
from app.core.domain.models import Advisor, Equipment, Holding, Intervention, Plot, Product
from app.core.domain.states import LifecycleState

advisor = Advisor(full_name="Pedro Flores Navarro", dni="12345678Z",
                  ropo_number="ROPO-AS-30-0001", account_status="ACTIVE", id=uuid4())
holding = Holding(advisor_id=advisor.id, owner_name="Pepe García",
                  owner_nif="87654321X", rea_regepa_number="REA-30-12345", id=uuid4())
plot = Plot(holding_id=holding.id, voice_alias="Finca de Pepe", crop="Limonero",
            variety="Fino", enclosure_area_ha=5.0, sigpac_province="30",
            sigpac_municipality="001", sigpac_polygon="12", sigpac_parcel="34",
            sigpac_enclosure="1", id=uuid4())
product = Product(registration_number="ES-00123", trade_name="Abamectina",
                  active_substance="abamectina 1.8%", authorized=True,
                  max_allowed_dose=2.0, dose_unit="L/ha", pre_harvest_interval_days=14)
equipment = Equipment(holding_id=holding.id, equipment_alias="tractor",
                      equipment_type="TRACTOR", roma_number="ROMA-30-98765", id=uuid4())
intervention = Intervention(
    transaction_id=uuid4(), lifecycle_state=LifecycleState.PRESCRIBED,
    advisor_id=advisor.id, holding_id=holding.id, plot_id=plot.id,
    product_registration_number=product.registration_number, equipment_id=equipment.id,
    prescription_date=datetime(2026, 6, 16, 8, 30, tzinfo=timezone.utc),
    planned_date=date(2026, 6, 19), prescribed_dose=1.5, dose_unit="L/ha",
    target_pest="araña roja",
    justification="Superación del umbral de daño económico en monitoreo semanal.",
)

pdf = ReportLabPdfGenerator().generate_prescription(
    intervention=intervention, advisor=advisor, holding=holding,
    plot=plot, product=product, equipment=equipment,
)
assert pdf.startswith(b"%PDF"), "output is not a PDF"

out = Path(__file__).resolve().parents[1] / "sample_prescription.pdf"
out.write_bytes(pdf)
print(f"OK · {len(pdf)} bytes -> {out}")
