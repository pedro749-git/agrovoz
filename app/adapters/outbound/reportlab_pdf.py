"""ReportLab adapter: renders the prescription PDF (RD 1311/2012).

Spanish legal document. Timestamps are rendered in Europe/Madrid (hard rule 9:
UTC in the DB, Madrid only in PDFs).
"""

import io
from datetime import date, datetime
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.domain.models import (
    Advisor,
    Equipment,
    Holding,
    Intervention,
    Plot,
    Product,
    Validation,
    ValidationType,
)
from app.core.ports.pdf_generator import PdfGenerator

# Spanish labels for the validation PDF (legal document -> user-facing Spanish).
_VALIDATION_TYPE_LABEL = {
    ValidationType.MID_CYCLE: "Intermedia (durante el ciclo)",
    ValidationType.FINAL: "Final (cierre de campaña)",
}

_MADRID = ZoneInfo("Europe/Madrid")
_UTC = ZoneInfo("UTC")
_DASH = "—"  # shown for empty/optional fields


def _v(value) -> str:
    """Field value as display text; empty/None -> em dash."""
    if value is None or value == "":
        return _DASH
    return str(value)


def _fmt_datetime(dt: datetime | None) -> str:
    if dt is None:
        return _DASH
    if dt.tzinfo is None:  # treat naive as UTC (the DB stores UTC)
        dt = dt.replace(tzinfo=_UTC)
    return dt.astimezone(_MADRID).strftime("%d/%m/%Y %H:%M")


def _fmt_date(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else _DASH


class ReportLabPdfGenerator(PdfGenerator):
    def __init__(self) -> None:
        base = getSampleStyleSheet()
        self._title = ParagraphStyle(
            "Title", parent=base["Title"], fontSize=15, spaceAfter=2
        )
        self._subtitle = ParagraphStyle(
            "Subtitle", parent=base["Normal"], fontSize=9,
            textColor=colors.HexColor("#555555"), alignment=1,
        )
        self._heading = ParagraphStyle(
            "Heading", parent=base["Heading2"], fontSize=11,
            textColor=colors.white, backColor=colors.HexColor("#2e7d32"),
            leftIndent=4, spaceBefore=6, spaceAfter=4, leading=16,
        )
        self._label = ParagraphStyle("Label", parent=base["Normal"], fontSize=9)
        self._value = ParagraphStyle("Value", parent=base["Normal"], fontSize=9)

    def generate_prescription(
        self,
        *,
        intervention: Intervention,
        advisor: Advisor,
        holding: Holding,
        plot: Plot,
        product: Product,
        equipment: Equipment | None = None,
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=2 * cm, bottomMargin=2 * cm,
            leftMargin=2 * cm, rightMargin=2 * cm,
            title="Prescripción de tratamiento fitosanitario",
        )

        sigpac = ":".join([
            plot.sigpac_province, plot.sigpac_municipality, plot.sigpac_polygon,
            plot.sigpac_parcel, plot.sigpac_enclosure,
        ])
        crop = plot.crop + (f" ({plot.variety})" if plot.variety else "")
        dose = f"{_v(intervention.prescribed_dose)} {intervention.dose_unit or product.dose_unit or ''}".strip()
        phi = (
            f"{product.pre_harvest_interval_days} días"
            if product.pre_harvest_interval_days is not None else _DASH
        )

        story: list = [
            Paragraph("PRESCRIPCIÓN DE TRATAMIENTO FITOSANITARIO", self._title),
            Paragraph(
                "Asesoramiento en Gestión Integrada de Plagas (GIP) — RD 1311/2012",
                self._subtitle,
            ),
            Spacer(1, 0.6 * cm),
        ]
        story += self._section("Asesor (técnico GIP)", [
            ("Nombre y apellidos", _v(advisor.full_name)),
            ("DNI", _v(advisor.dni)),
            ("Nº ROPO (asesoramiento)", _v(advisor.ropo_number)),
        ])
        story += self._section("Explotación", [
            ("Titular", _v(holding.owner_name)),
            ("NIF", _v(holding.owner_nif)),
            ("Nº REA/REGEPA", _v(holding.rea_regepa_number)),
        ])
        story += self._section("Parcela", [
            ("Identificación", _v(plot.voice_alias)),
            ("Cultivo", _v(crop)),
            ("Recinto SIGPAC (P:M:Pol:Par:Rec)", sigpac),
            ("Superficie del recinto", f"{_v(plot.enclosure_area_ha)} ha"),
        ])
        story += self._section("Tratamiento prescrito", [
            ("Producto (nombre comercial)", _v(product.trade_name)),
            ("Materia activa", _v(product.active_substance)),
            ("Nº registro MAPA", _v(product.registration_number)),
            ("Dosis", dose),
            ("Plaga / organismo objetivo", _v(intervention.target_pest)),
            ("Justificación", _v(intervention.justification)),
            ("Equipo previsto", _v(equipment.equipment_alias if equipment else None)),
            ("Nº ROMA (equipo)", _v(equipment.roma_number if equipment else None)),
            ("Plazo de seguridad (PHI)", phi),
        ])
        story += self._section("Fechas", [
            ("Fecha de prescripción", _fmt_datetime(intervention.prescription_date)),
            ("Fecha prevista de aplicación", _fmt_date(intervention.planned_date)),
        ])
        story.append(Spacer(1, 1.2 * cm))
        story.append(Paragraph(
            "Firma del asesor: ____________________________", self._value
        ))

        doc.build(story)
        return buffer.getvalue()

    def generate_validation(
        self,
        *,
        validation: Validation,
        advisor: Advisor,
        holding: Holding,
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=2 * cm, bottomMargin=2 * cm,
            leftMargin=2 * cm, rightMargin=2 * cm,
            title="Validación de registros fitosanitarios",
        )

        period = f"{_fmt_date(validation.period_start)} – {_fmt_date(validation.period_end)}"
        conformity = "CONFORME" if validation.conformity else "NO CONFORME"
        type_label = _VALIDATION_TYPE_LABEL.get(validation.type, _v(validation.type))

        story: list = [
            Paragraph("VALIDACIÓN DE REGISTROS FITOSANITARIOS", self._title),
            Paragraph(
                "Conformidad del asesor GIP sobre el cuaderno de la explotación "
                "— RD 1311/2012",
                self._subtitle,
            ),
            Spacer(1, 0.6 * cm),
        ]
        story += self._section("Asesor (técnico GIP)", [
            ("Nombre y apellidos", _v(advisor.full_name)),
            ("DNI", _v(advisor.dni)),
            ("Nº ROPO (asesoramiento)", _v(advisor.ropo_number)),
        ])
        story += self._section("Explotación", [
            ("Titular", _v(holding.owner_name)),
            ("NIF", _v(holding.owner_nif)),
            ("Nº REA/REGEPA", _v(holding.rea_regepa_number)),
        ])
        story += self._section("Validación", [
            ("Campaña", _v(validation.campaign)),
            ("Tipo", type_label),
            ("Periodo validado", period),
            ("Nº de intervenciones", _v(validation.intervention_count)),
            ("Resultado", conformity),
            ("Observaciones", _v(validation.remarks)),
            ("Fecha de la validación", _fmt_datetime(validation.validation_date)),
        ])
        story.append(Spacer(1, 1.2 * cm))
        story.append(Paragraph(
            "Firma del asesor: ____________________________", self._value
        ))

        doc.build(story)
        return buffer.getvalue()

    def _section(self, title: str, rows: list[tuple[str, str]]) -> list:
        data = [
            [Paragraph(label, self._label), Paragraph(value, self._value)]
            for label, value in rows
        ]
        table = Table(data, colWidths=[6 * cm, 11 * cm])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#dddddd")),
        ]))
        return [Paragraph(title, self._heading), table, Spacer(1, 0.4 * cm)]
