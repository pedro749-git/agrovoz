"""Inbound presenters: shape domain entities into the API's JSON responses.

Pure functions, NO I/O and NO FastAPI — split out of ``api.py`` so that module
stays routing + error mapping while the JSON shaping lives here (easy to read,
easy to test in isolation). Projections, NOT the raw entities: internal
traceability fields (raw_transcription, prompt_version, storage keys) never
leave the boundary. Field names are English (data identifiers); the PWA maps
them to Spanish labels.

The one presenter that needs I/O (signing a PDF link) stays in ``api.py`` —
these are all synchronous and dependency-free on purpose.
"""

from app.core.domain.models import (
    Equipment,
    Holding,
    Intervention,
    Plot,
    Validation,
)
from app.core.services.registration_pipeline import PreviewResult


def _iso(value) -> str | None:
    """ISO string for a date/datetime, or None. Both have .isoformat()."""
    return value.isoformat() if value is not None else None


def _sigpac(plot: Plot) -> str:
    """The plot's SIGPAC reference as province:municipality:polygon:parcel:enclosure."""
    return ":".join(
        (
            plot.sigpac_province,
            plot.sigpac_municipality,
            plot.sigpac_polygon,
            plot.sigpac_parcel,
            plot.sigpac_enclosure,
        )
    )


def preview_result(preview: PreviewResult) -> dict:
    """FLUJO A phase-1 projection (M8): the transcription, the CANONICALIZED fields
    for the review form, and a per-identity resolution marker so the form shows a
    ✓ (matched a catalog row) or a ⚠️ (fix it). The plot carries crop + SIGPAC when
    matched, so the advisor can confirm it is the right parcela. product/equipment
    only carry ``found`` — their canonical name is already in ``fields``."""
    plot = preview.plot
    return {
        "transcription": preview.transcription,
        "fields": preview.fields.model_dump(),
        "resolution": {
            "plot": {
                "found": plot is not None,
                "crop": plot.crop if plot else None,
                "sigpac": _sigpac(plot) if plot else None,
            },
            "product": {"found": preview.product is not None},
            "equipment": {"found": preview.equipment is not None},
        },
    }


def record_fields(intervention: Intervention) -> dict:
    """Common record fields shared by the create response and the list endpoint.

    ``has_pdf`` lets the list show a PDF affordance without signing a URL per row.
    """
    dose = intervention.applied_dose or intervention.prescribed_dose
    return {
        "id": str(intervention.id),
        "transaction_id": str(intervention.transaction_id),
        "lifecycle_state": intervention.lifecycle_state.value,
        # DB-generated UTC timestamp. The PWA Home groups by day (in
        # Europe/Madrid) to show "today's" records, so the list needs it; the
        # device timestamp lives on prescription_date/treatment_date and is not
        # set for OBSERVATIONs, so created_at is the one date every row carries.
        "created_at": _iso(intervention.created_at),
        "observation": intervention.observation,
        "product_registration_number": intervention.product_registration_number,
        "dose": dose,
        "dose_unit": intervention.dose_unit,
        "target_pest": intervention.target_pest,
        "earliest_harvest_date": _iso(intervention.earliest_harvest_date),
        # Weather captured at execution (None until EXECUTED, or when deferred).
        # audit_state lets the PWA flag a record whose weather is still pending.
        "temperature_c": intervention.temperature_c,
        "relative_humidity_pct": intervention.relative_humidity_pct,
        "wind_speed_kmh": intervention.wind_speed_kmh,
        "wind_direction": intervention.wind_direction,
        "audit_state": intervention.audit_state,
        # ITEAF inspection expired/unrecorded on the treatment day: a
        # non-blocking notice the PWA surfaces on executed records.
        "iteaf_warning": intervention.iteaf_warning,
        "has_pdf": intervention.prescription_pdf_key is not None,
    }


def intervention_detail(
    intervention: Intervention,
    plot: Plot | None,
    holding: Holding | None,
    equipment: Equipment | None,
) -> dict:
    """Full single-record projection for the detail screen: the list fields PLUS
    the prescription/execution detail, the raw transcription ("lo que dictaste"),
    and the plot/holding/equipment context. Nested context blocks are None when
    the related row is missing (e.g. an OBSERVATION has no equipment)."""
    data = record_fields(intervention)
    data.update(
        {
            # Prescription block.
            "prescription_date": _iso(intervention.prescription_date),
            "planned_date": _iso(intervention.planned_date),
            "prescribed_dose": intervention.prescribed_dose,
            "justification": intervention.justification,
            "previous_alternatives": intervention.previous_alternatives,
            # Execution block (the real applied data).
            "treatment_date": _iso(intervention.treatment_date),
            "applied_dose": intervention.applied_dose,
            "treated_area_ha": intervention.treated_area_ha,
            "spray_volume_l_ha": intervention.spray_volume_l_ha,
            "operator_name": intervention.operator_name,
            "operator_ropo": intervention.operator_ropo,
            "delivery_note_number": intervention.delivery_note_number,
            # Assessment block (Phase 4): how well it worked, when, and why.
            "effectiveness": (
                intervention.effectiveness.value
                if intervention.effectiveness
                else None
            ),
            "effectiveness_date": _iso(intervention.effectiveness_date),
            "effectiveness_notes": intervention.effectiveness_notes,
            # What the advisor dictated (audio itself is not persisted yet).
            "raw_transcription": intervention.raw_transcription,
            # Context the detail renders (the where, the who, the with-what).
            "plot": (
                {
                    "voice_alias": plot.voice_alias,
                    "crop": plot.crop,
                    "variety": plot.variety,
                    "enclosure_area_ha": plot.enclosure_area_ha,
                    "sigpac": _sigpac(plot),
                }
                if plot
                else None
            ),
            "holding": (
                {
                    "owner_name": holding.owner_name,
                    "rea_regepa_number": holding.rea_regepa_number,
                }
                if holding
                else None
            ),
            "equipment": (
                {
                    "equipment_alias": equipment.equipment_alias,
                    "equipment_type": equipment.equipment_type,
                    "roma_number": equipment.roma_number,
                    "iteaf_inspection_date": _iso(equipment.iteaf_inspection_date),
                }
                if equipment
                else None
            ),
        }
    )
    return data


def validation_fields(validation: Validation) -> dict:
    """Projection of a signed campaign validation. ``has_pdf`` lets the list show
    a PDF affordance without signing a URL per row; the presigned link is signed
    on demand (create response or GET /pdf)."""
    return {
        "id": str(validation.id),
        "holding_id": str(validation.holding_id),
        "campaign": validation.campaign,
        "type": validation.type.value,
        "validation_date": _iso(validation.validation_date),
        "conformity": validation.conformity,
        "period_start": _iso(validation.period_start),
        "period_end": _iso(validation.period_end),
        "intervention_count": validation.intervention_count,
        "remarks": validation.remarks,
        "has_pdf": validation.validation_pdf_key is not None,
        "created_at": _iso(validation.created_at),
    }


def holding_overview(
    holding: Holding, plots: list[Plot], validations: list[Validation]
) -> dict:
    """A holding with its plots and all its validations — one entry of the PWA
    validation screen (grouped by holding, rule 6: the validation is the
    HOLDING's, not a plot's). The PWA groups the validations by campaign and
    derives the 0/2 counter client-side."""
    return {
        "id": str(holding.id),
        "owner_name": holding.owner_name,
        "owner_nif": holding.owner_nif,
        "rea_regepa_number": holding.rea_regepa_number,
        "plots": [
            {"voice_alias": p.voice_alias, "crop": p.crop} for p in plots
        ],
        "validations": [validation_fields(v) for v in validations],
    }
