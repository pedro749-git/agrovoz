"""Inbound FastAPI app.

The PWA REST API (M4+): synchronous JSON endpoints the advisor's UI awaits —
FLUJO A (record), B (execution) and C (assessment / campaign validation).

The file is laid out in sections (see the banner comments): app + error shape,
exception handlers, health, and the PWA REST API. JSON shaping lives in
``presenters`` — this module is routing + error mapping.
"""

import logging
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from app.adapters.inbound import presenters
from app.adapters.inbound.auth import (
    AuthError,
    AuthUser,
    current_advisor_id,
    current_auth_user,
)
from app.config import container
from app.config.settings import settings
from app.core.domain.errors import DomainError, InfrastructureError
from app.core.domain.models import (
    Effectiveness,
    Intervention,
    Validation,
    ValidationType,
)
from app.core.domain.states import LifecycleState

logger = logging.getLogger(__name__)

# Configure logging once, at the process entry point (uvicorn imports this
# module). Puts a handler on the root logger so every ``app.*`` logger — INFO
# and above — is shown, with a timestamp and the emitting module.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# The Supabase client talks over httpx, which logs every REST call ("HTTP
# Request: POST ...") at INFO. That is noise next to our own timing logs, so we
# raise httpx/httpcore to WARNING: their per-request lines are hidden, but real
# problems (a failed connection) still surface.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Domain errors that mean "the advisor referenced something that does not
# exist" map to 404; every other business-rule violation is a 422.
_NOT_FOUND_CODES = {
    "PLOT_NOT_FOUND",
    "EQUIPMENT_NOT_FOUND",
    "INTERVENTION_NOT_FOUND",
    "HOLDING_NOT_FOUND",
}

# The advisor's civil timezone. A "day" in the UI (today's list, a history range)
# is decided here (rule 9), then mapped to a precise UTC window for the DB.
_MADRID = ZoneInfo("Europe/Madrid")

app = FastAPI(title="GIP Advisor API")


def _error(status: int, code: str, mensaje: str) -> JSONResponse:
    """The single API error shape (spec §7): English code, Spanish message."""
    return JSONResponse(status_code=status, content={"error": code, "mensaje": mensaje})


# ══════════════════════════════════════════════════════════════════════════════
# Exception handlers — one error policy shared by every HTTP route
# ══════════════════════════════════════════════════════════════════════════════


@app.exception_handler(DomainError)
async def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    """Business-rule violation -> 404/422 with the agronomist-readable message.

    The error message IS the user feedback (it is written in Spanish at the
    raise site), so it goes straight into ``mensaje``. Registered on the app
    once so every HTTP route shares one policy.
    """
    status = 404 if exc.code in _NOT_FOUND_CODES else 422
    return _error(status, exc.code, str(exc))


@app.exception_handler(AuthError)
async def _auth_error_handler(_: Request, exc: AuthError) -> JSONResponse:
    """Missing/invalid token or a user that is not an advisor -> 401."""
    return _error(401, "AUTH_ERROR", str(exc))


@app.exception_handler(InfrastructureError)
async def _infra_error_handler(_: Request, exc: InfrastructureError) -> JSONResponse:
    """External-provider failure (Qwen, OSS, ...) -> 503. Not the advisor's
    fault and the cause may leak vendor details, so the message stays generic
    and the traceback goes to the log."""
    logger.exception("Infrastructure failure handling an API request")
    return _error(
        503,
        "INFRASTRUCTURE_ERROR",
        "Fallo técnico procesando el audio. Inténtalo de nuevo.",
    )


@app.exception_handler(Exception)
async def _unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Safety net for any error not translated above — a stray KeyError, a
    serialization bug, etc. Provider failures ARE translated (Qwen/OSS ->
    InfrastructureError, Supabase -> RepositoryError), so this should fire only
    on genuine bugs. Returns a clean 500 in our shape instead of FastAPI's
    default and logs the traceback.
    More specific handlers above still win — FastAPI dispatches by exception
    type, not registration order.
    """
    logger.exception("Unhandled error in an API request")
    return _error(500, "INTERNAL_ERROR", "Error inesperado. Inténtalo de nuevo.")


# ══════════════════════════════════════════════════════════════════════════════
# Health
# ══════════════════════════════════════════════════════════════════════════════


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════════════════════
# PWA REST API — the live inbound (FLUJO A/B/C), synchronous JSON the UI awaits
# ══════════════════════════════════════════════════════════════════════════════


@app.post("/api/bootstrap")
async def bootstrap(
    user: AuthUser = Depends(current_auth_user),
) -> JSONResponse:
    """Provision a demo advisor + sandbox for a just-signed-up user (hackathon
    self-signup, TEMPORARY — see docs/decisions.md and settings.hackathon_signup_enabled).

    This is the ONE endpoint that runs before an advisor row exists, so it uses
    ``current_auth_user`` (verifies the token only) instead of
    ``current_advisor_id`` (which would 401 a user with no advisor yet). The
    service is idempotent: the PWA may call it on every "just signed up" render.

    When the flag is off (the default / permanent state) the endpoint pretends
    not to exist — a 404 — so the closed-login design leaks nothing about it."""
    if not settings.hackathon_signup_enabled:
        return _error(404, "NOT_FOUND", "No encontrado.")
    advisor = await container.onboarding_service.bootstrap_demo_advisor(
        user.id, user.email
    )
    return JSONResponse(content={"advisor_id": str(advisor.id)})


@app.post("/api/records")
async def create_record(
    audio: UploadFile = File(...),
    transaction_id: UUID = Form(...),
    device_timestamp: datetime = Form(...),
    advisor_id: UUID = Depends(current_advisor_id),
) -> JSONResponse:
    """FLUJO A for the PWA: an audio note -> persisted intervention (spec §7).

    This is SYNCHRONOUS: the advisor's UI waits for the outcome (a saved record
    to list, or a 422 dose/area error to show), so we
    process inline and let the registered exception handlers translate any
    failure into the {"error", "mensaje"} shape.

    ``advisor_id`` comes from the verified Supabase JWT (``current_advisor_id``),
    not a request field — the record is attributed to whoever is logged in. The
    client still sends its own ``transaction_id`` (crypto.randomUUID) and the
    device timestamp (hard rules 2 and 3).
    """
    intervention = await container.pipeline.register(
        audio=await audio.read(),
        advisor_id=advisor_id,
        transaction_id=transaction_id,
        device_timestamp=device_timestamp,
    )
    return JSONResponse(content=await _record_response(intervention))


@app.get("/api/interventions")
async def list_interventions(
    state: LifecycleState | None = None,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    advisor_id: UUID = Depends(current_advisor_id),
) -> JSONResponse:
    """The advisor's interventions for the PWA Home list and history (spec §7).

    Scoped to the authenticated advisor (same dependency as POST). Optional
    ``?state=`` filters by lifecycle; FastAPI validates it against the enum, so a
    bad value is a 422 before this runs.

    ``?from=&to=`` are civil dates AS SEEN IN SPAIN (rule 9), both inclusive: the
    Home list asks for today (``from==to``), the history screen for a wider span.
    We turn them into the exact UTC window ``[from 00:00 Madrid, (to+1d) 00:00
    Madrid)`` here — DST-correct via zoneinfo — so the DB filter on the UTC
    ``created_at`` is precise, not the day-boundary fuzz a naive civil-date
    comparison would give. Newest first. No presigned PDF links here (one OSS
    call per row would not scale) — each item carries ``has_pdf`` and the detail
    view signs the URL on demand.
    """
    since = (
        datetime.combine(date_from, time.min, _MADRID).astimezone(timezone.utc)
        if date_from is not None
        else None
    )
    until = (
        datetime.combine(date_to + timedelta(days=1), time.min, _MADRID).astimezone(
            timezone.utc
        )
        if date_to is not None
        else None
    )
    interventions = await container.repository.list_interventions(
        advisor_id, state=state, since=since, until=until
    )
    return JSONResponse(content=[presenters.record_fields(i) for i in interventions])


@app.get("/api/interventions/{intervention_id}")
async def get_intervention_detail(
    intervention_id: UUID,
    advisor_id: UUID = Depends(current_advisor_id),
) -> JSONResponse:
    """One intervention in full for the PWA detail screen.

    Scoped to the authenticated advisor, so an unknown OR foreign id is an
    indistinguishable 404 (you cannot probe what is not yours). Richer than the
    list projection: it adds the prescription/execution detail and the raw
    transcription, plus the plot/holding/equipment context the detail renders.
    Three extra reads (plot, holding, equipment) are fine for a single record —
    this is exactly why the list stays lean and does NOT do them per row.
    """
    intervention = await container.repository.get_intervention(
        intervention_id, advisor_id
    )
    if intervention is None:
        return _error(404, "INTERVENTION_NOT_FOUND", "No encuentro ese registro.")

    plot = await container.repository.get_plot(intervention.plot_id)
    holding = await container.repository.get_holding(intervention.holding_id)
    equipment = (
        await container.repository.get_equipment(intervention.equipment_id)
        if intervention.equipment_id is not None
        else None
    )
    return JSONResponse(
        content=presenters.intervention_detail(intervention, plot, holding, equipment)
    )


@app.get("/api/interventions/{intervention_id}/pdf")
async def get_intervention_pdf(
    intervention_id: UUID,
    advisor_id: UUID = Depends(current_advisor_id),
) -> JSONResponse:
    """Sign the prescription PDF link ON DEMAND (spec §7 — the list deliberately
    omits it; signing every row would be N OSS calls). Returns a short-lived
    presigned URL the PWA opens in a new tab.

    Scoped to the authenticated advisor: ``get_intervention`` filters by
    advisor_id, so requesting another advisor's id is an indistinguishable 404
    (you cannot probe what is not yours). A record without a PDF (an OBSERVATION,
    or a prescription whose PDF render/upload failed) is also a 404 — there is no
    document to hand back. A signing failure surfaces as the 503 from the
    InfrastructureError handler.
    """
    intervention = await container.repository.get_intervention(
        intervention_id, advisor_id
    )
    if intervention is None:
        return _error(404, "INTERVENTION_NOT_FOUND", "No encuentro ese registro.")
    if intervention.prescription_pdf_key is None:
        return _error(404, "PDF_NOT_FOUND", "Este registro no tiene PDF de prescripción.")

    # The DB key may outlive its object (uploaded to another bucket, deleted,
    # ...). Check before signing so a missing object is a clean 404, not the
    # provider's raw XML error in the browser.
    if not await container.storage.exists(intervention.prescription_pdf_key):
        return _error(404, "PDF_NOT_FOUND", "El PDF de este registro no está disponible.")

    url = await container.storage.presigned_url(intervention.prescription_pdf_key)
    return JSONResponse(content={"pdf_url": url})


@app.patch("/api/interventions/{intervention_id}/execution")
async def confirm_execution(
    intervention_id: UUID,
    treatment_date: datetime = Form(...),
    applied_dose: float | None = Form(None),
    treated_area_ha: float | None = Form(None),
    operator_name: str | None = Form(None),
    operator_ropo: str | None = Form(None),
    spray_volume_l_ha: float | None = Form(None),
    delivery_note_number: str | None = Form(None),
    advisor_id: UUID = Depends(current_advisor_id),
) -> JSONResponse:
    """FLUJO B (M5): confirm a prescription's execution with the real applied
    data — PRESCRIBED -> EXECUTED, re-validating legality with the real dose/area.

    Synchronous like POST /api/records (the UI waits for the updated record, or a
    422 dose/area/state error). Form-encoded for consistency with create_record.
    ``treatment_date`` is the real application date the PWA prefills with the
    device clock (editable); the other fields default to the prescribed/holding
    values when omitted. Scoped to the authenticated advisor, so an unknown id is
    a 404. Weather is NOT captured here yet (next M5 step)."""
    intervention = await container.execution_service.confirm(
        intervention_id=intervention_id,
        advisor_id=advisor_id,
        treatment_date=treatment_date,
        applied_dose=applied_dose,
        treated_area_ha=treated_area_ha,
        operator_name=operator_name,
        operator_ropo=operator_ropo,
        spray_volume_l_ha=spray_volume_l_ha,
        delivery_note_number=delivery_note_number,
    )
    return JSONResponse(content=await _record_response(intervention))


@app.patch("/api/interventions/{intervention_id}/effectiveness")
async def assess_effectiveness(
    intervention_id: UUID,
    effectiveness: Effectiveness = Form(...),
    effectiveness_date: date = Form(...),
    effectiveness_notes: str | None = Form(None),
    advisor_id: UUID = Depends(current_advisor_id),
) -> JSONResponse:
    """FLUJO C (M6): rate an executed treatment's effectiveness — EXECUTED ->
    ASSESSED (Phase 4).

    Synchronous like the execution confirm. ``effectiveness`` is validated
    against the enum at the boundary (a bad value is a 422 before this runs).
    ``effectiveness_date`` is when the advisor judged the result, prefilled by
    the PWA with the device date (editable — the assessment happens days after
    the treatment). ``effectiveness_notes`` is the optional reason the advisor
    dictated; the PWA transcribes it via POST /api/transcribe first, so it
    arrives here as already-reviewed text. Scoped to the authenticated advisor,
    so an unknown id is a 404."""
    intervention = await container.assessment_service.assess(
        intervention_id=intervention_id,
        advisor_id=advisor_id,
        effectiveness=effectiveness,
        effectiveness_date=effectiveness_date,
        effectiveness_notes=effectiveness_notes,
    )
    return JSONResponse(content=await _record_response(intervention))


@app.post("/api/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    advisor_id: UUID = Depends(current_advisor_id),
) -> JSONResponse:
    """Speech-to-text ONLY — no extraction, no persistence (M6).

    The PWA uses this for the assessment reason: the advisor dictates, we
    transcribe, and the text goes into an editable textarea the advisor reviews
    before submitting the assessment. Kept separate from POST /api/records (which
    also extracts fields and saves a record) precisely so the advisor sees and
    can correct what Qwen heard before it reaches the legal record. Authenticated
    like every PWA endpoint; a provider failure surfaces as the 503 from the
    InfrastructureError handler."""
    text = await container.transcriber.transcribe(await audio.read())
    return JSONResponse(content={"text": text})


@app.get("/api/holdings")
async def list_holdings(
    advisor_id: UUID = Depends(current_advisor_id),
) -> JSONResponse:
    """The advisor's holdings with their plots and validations — the PWA
    validation screen (M7, grouped by holding: the validation is the HOLDING's,
    not a plot's, rule 6).

    Scoped to the authenticated advisor. One follow-up read per holding (plots +
    validations) is fine — an advisor has few holdings, the same reasoning that
    keeps the intervention list lean and does its extra reads only on the detail.
    The PWA groups the validations by campaign and derives the 0/2 counter."""
    holdings = await container.repository.list_holdings(advisor_id)
    overview = []
    for holding in holdings:
        plots = await container.repository.list_plots(holding.id)
        validations = await container.repository.list_validations(holding.id)
        overview.append(presenters.holding_overview(holding, plots, validations))
    return JSONResponse(content=overview)


@app.post("/api/holdings/{holding_id}/validations")
async def create_validation(
    holding_id: UUID,
    campaign: str = Form(...),
    validation_type: ValidationType = Form(...),
    conformity: bool = Form(...),
    validation_date: datetime = Form(...),
    remarks: str | None = Form(None),
    advisor_id: UUID = Depends(current_advisor_id),
) -> JSONResponse:
    """FLUJO C (M7): the advisor signs a campaign validation over a holding's
    interventions — mandatory twice per campaign (MID_CYCLE + FINAL, Phase 5).

    Synchronous like the other write endpoints. ``validation_type`` is validated
    against the enum at the boundary (a bad value is a 422 before this runs).
    ``validation_date`` is the device timestamp (the advisor may sign offline).
    The service derives the period covered and counts the interventions in it. A
    non-conform validation must carry ``remarks`` (else 422). The holding is
    scoped to the authenticated advisor, so an unknown OR foreign id is a 404."""
    validation = await container.campaign_validation_service.validate_campaign(
        holding_id=holding_id,
        advisor_id=advisor_id,
        campaign=campaign,
        validation_type=validation_type,
        conformity=conformity,
        validation_date=validation_date,
        remarks=remarks,
    )
    return JSONResponse(content=await _validation_response(validation))


@app.get("/api/validations/{validation_id}/pdf")
async def get_validation_pdf(
    validation_id: UUID,
    advisor_id: UUID = Depends(current_advisor_id),
) -> JSONResponse:
    """Sign the signed-validation PDF link ON DEMAND (M7.3) — the list carries
    ``has_pdf`` and this signs the URL only when the advisor opens it, like the
    prescription PDF.

    Scoped to the authenticated advisor: ``get_validation`` filters by advisor_id,
    so a foreign id is an indistinguishable 404. A validation whose PDF
    render/upload failed (saved without a key, best-effort) is also a 404 — there
    is no document yet. A signing failure surfaces as the 503 from the
    InfrastructureError handler."""
    validation = await container.repository.get_validation(validation_id, advisor_id)
    if validation is None:
        return _error(404, "VALIDATION_NOT_FOUND", "No encuentro esa validación.")
    if validation.validation_pdf_key is None:
        return _error(404, "PDF_NOT_FOUND", "Esta validación no tiene PDF.")

    # The DB key may outlive its object; check before signing so a missing object
    # is a clean 404, not the provider's raw XML error in the browser.
    if not await container.storage.exists(validation.validation_pdf_key):
        return _error(404, "PDF_NOT_FOUND", "El PDF de esta validación no está disponible.")

    url = await container.storage.presigned_url(validation.validation_pdf_key)
    return JSONResponse(content={"pdf_url": url})


async def _record_response(intervention: Intervention) -> dict:
    """Create-response: the common fields PLUS a best-effort presigned PDF link.

    The only presenter that does I/O, so it stays here (next to the container)
    instead of in the pure ``presenters`` module. Signing is per-record I/O, so
    it lives here (one record) and NOT in the list endpoint. A signing failure
    must NOT turn an already-saved record into an error response — we log and
    return the record without the link.
    """
    data = presenters.record_fields(intervention)
    data["pdf_url"] = None
    if intervention.prescription_pdf_key:
        try:
            data["pdf_url"] = await container.storage.presigned_url(
                intervention.prescription_pdf_key
            )
        except Exception:
            logger.warning(
                "No se pudo firmar el enlace del PDF (OSS); respuesta sin enlace",
                exc_info=True,
            )
    return data


async def _validation_response(validation: Validation) -> dict:
    """Create-response for a campaign validation: the projection PLUS a
    best-effort presigned link to the signed PDF. Mirrors ``_record_response`` —
    a signing failure (or a validation saved without a key because its PDF
    render/upload failed) must NOT turn an already-saved validation into an
    error; we log and return it without the link."""
    data = presenters.validation_fields(validation)
    data["pdf_url"] = None
    if validation.validation_pdf_key:
        try:
            data["pdf_url"] = await container.storage.presigned_url(
                validation.validation_pdf_key
            )
        except Exception:
            logger.warning(
                "No se pudo firmar el enlace del PDF de validación (OSS); "
                "respuesta sin enlace",
                exc_info=True,
            )
    return data
