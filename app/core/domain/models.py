"""Domain entities (spec §5) — plain dataclasses mirroring the DB tables
(supabase/migrations/*_estructura_inicial_rls.sql).

Conventions:
- ``id``/``created_at``/``updated_at`` default to None: the DB generates them.
- ``deleted_at`` implements soft-delete — legal records are never deleted.
- Timestamps are UTC in the DB; Europe/Madrid only when rendering PDFs.
"""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.core.domain.states import LifecycleState


@dataclass
class Advisor:
    """The GIP advisor: prescribes interventions and validates holdings."""

    full_name: str
    dni: str
    ropo_number: str  # ROPO sector "asesoramiento"
    account_status: str = "PENDING"  # PENDING | ACTIVE | SUSPENDED
    auth_user_id: UUID | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass
class Holding:
    """The holding (explotación): legal owner of the record/CUE,
    identified before the Administration by REA/REGEPA number + owner NIF."""

    advisor_id: UUID
    owner_name: str
    owner_nif: str
    rea_regepa_number: str
    # Default operator: if nobody says who applies, the owner does
    default_operator_name: str | None = None
    default_operator_ropo: str | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass
class Plot:
    """The where: a SIGPAC enclosure. The enclosure area caps the legally
    treatable area."""

    holding_id: UUID
    voice_alias: str  # "Finca de Pepe" (Spanish, what the advisor dictates)
    crop: str
    enclosure_area_ha: float
    sigpac_province: str
    sigpac_municipality: str
    sigpac_polygon: str
    sigpac_parcel: str
    sigpac_enclosure: str
    variety: str | None = None
    lat: float | None = None  # centroid: AEMET fallback when no GPS
    lon: float | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass
class Product:
    """Official MAPA vademecum entry (preloaded, read-only for advisors)."""

    registration_number: str  # MAPA registration number (natural PK)
    trade_name: str  # what the advisor dictates
    active_substance: str
    authorized: bool = True
    max_allowed_dose: float | None = None
    dose_unit: str | None = None  # 'L/ha', 'Kg/ha'
    pre_harvest_interval_days: int | None = None  # PHI (plazo de seguridad)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Equipment:
    """The with-what: ROMA registers the machine (ROPO registers the person)."""

    holding_id: UUID
    equipment_alias: str  # "tractor" (Spanish, what the advisor dictates)
    equipment_type: str | None = None  # TRACTOR | ATOMIZER | BACKPACK | DRONE
    roma_number: str | None = None
    aesa_registration: str | None = None  # drones only
    iteaf_inspection_date: date | None = None  # RD 1702/2011
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass
class WeatherData:
    """AEMET conditions captured when EXECUTION is confirmed (real
    application date — historical data if deferred), never at prescription."""

    temperature_c: float | None = None
    relative_humidity_pct: float | None = None
    wind_speed_kmh: float | None = None
    wind_direction: str | None = None


@dataclass
class Intervention:
    """The central event: an observation, prescription or execution.
    Belongs to the HOLDING (legal owner), recorded by the advisor."""

    transaction_id: UUID  # idempotency: client-generated, UNIQUE in DB
    lifecycle_state: LifecycleState
    advisor_id: UUID
    holding_id: UUID
    plot_id: UUID
    product_registration_number: str | None = None  # NULL if OBSERVATION
    equipment_id: UUID | None = None  # NULL if OBSERVATION

    # ── OBSERVATION block (Phase 1 — GIP surveillance) ──
    observation: str | None = None  # "3 capturas, bajo umbral"

    # ── PRESCRIPTION block (Phase 2 — the advisor indicates) ──
    prescription_date: datetime | None = None  # audio (device) timestamp
    planned_date: date | None = None
    prescribed_dose: float | None = None
    target_pest: str | None = None
    justification: str | None = None
    previous_alternatives: str | None = None  # autocompleted from plot
    #                                           OBSERVATIONs (≤60 days)
    prescription_pdf_key: str | None = None

    # ── EXECUTION block (Phase 3 — the CUE annotation) ──
    treatment_date: datetime | None = None  # REAL date, from the confirmation
    treated_area_ha: float | None = None  # ≤ plot.enclosure_area_ha
    applied_dose: float | None = None  # real (default: prescribed_dose)
    dose_unit: str | None = None
    spray_volume_l_ha: float | None = None
    operator_name: str | None = None
    operator_ropo: str | None = None  # the operator's own ROPO card
    delivery_note_number: str | None = None  # albarán/invoice number (FEGA)
    earliest_harvest_date: date | None = None  # treatment_date + product PHI
    iteaf_warning: bool = False  # ITEAF inspection expired

    # ── WEATHER block (AEMET, REAL execution date) ──
    temperature_c: float | None = None
    relative_humidity_pct: float | None = None
    wind_speed_kmh: float | None = None
    wind_direction: str | None = None
    gps_lat: float | None = None
    gps_lon: float | None = None

    # ── RESULT block (Phase 4) ──
    effectiveness: str | None = None  # GOOD | FAIR | POOR (UI: Buena/Regular/Mala)

    # ── TRACEABILITY block (internal) ──
    audio_storage_key: str | None = None
    execution_audio_key: str | None = None
    raw_transcription: str | None = None
    prompt_version: str | None = None
    audit_state: str | None = None  # VALID | WEATHER_PENDING | DOSE_ERROR |
    #                                 PRODUCT_ERROR | AREA_ERROR | FIELD_ERROR
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


@dataclass
class Validation:
    """Phase 5: the advisor's signed conformity over a holding's
    interventions — mandatory twice per campaign (MID_CYCLE + FINAL)."""

    advisor_id: UUID
    holding_id: UUID
    campaign: str  # '2026' or '2026-2027'
    type: str  # MID_CYCLE | FINAL (UNIQUE per holding+campaign in DB)
    validation_date: datetime
    conformity: bool
    period_start: date
    period_end: date
    intervention_count: int
    remarks: str | None = None  # mandatory if NOT conform (service enforces)
    validation_pdf_key: str | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
