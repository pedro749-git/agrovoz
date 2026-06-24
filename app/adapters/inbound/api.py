"""Inbound FastAPI app (M2).

The Telegram webhook is a thin inbound adapter over the core pipeline: it ACKs
immediately (Telegram retries on timeout), then processes in the background and
pushes the result back through the Notifier port. The future PWA (M4) will be a
second route calling the SAME pipeline — no business logic changes.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid5

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from app.adapters.inbound.auth import AuthError, current_advisor_id
from app.adapters.outbound.telegram import download_voice
from app.config import container
from app.config.settings import settings
from app.core.domain.errors import DomainError, InfrastructureError
from app.core.domain.models import Intervention
from app.core.domain.states import LifecycleState

logger = logging.getLogger(__name__)

# Fixed namespace to derive deterministic idempotency keys from Telegram
# updates (any constant UUID works; it just must never change).
_TELEGRAM_NS = UUID("9e3a7c1f-5b2d-4e8a-bf6c-1d2e3f4a5b6c")

# Domain errors that mean "the advisor referenced something that does not
# exist" map to 404; every other business-rule violation is a 422.
_NOT_FOUND_CODES = {"PLOT_NOT_FOUND", "EQUIPMENT_NOT_FOUND"}

app = FastAPI(title="GIP Advisor API")


def _error(status: int, code: str, mensaje: str) -> JSONResponse:
    """The single API error shape (spec §7): English code, Spanish message."""
    return JSONResponse(status_code=status, content={"error": code, "mensaje": mensaje})


@app.exception_handler(DomainError)
async def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    """Business-rule violation -> 404/422 with the agronomist-readable message.

    The error message IS the user feedback (it is written in Spanish at the
    raise site), so it goes straight into ``mensaje``. Registered on the app
    once so every HTTP route shares one policy — the Telegram webhook keeps its
    own try/except because it answers over chat, not HTTP.
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
    """Safety net for any error not translated above — a raw Supabase/PostgREST
    failure (the repository adapter does not yet wrap its errors as
    InfrastructureError; see decisions.md), a stray KeyError, etc. Returns a
    clean 500 in our shape instead of FastAPI's default and logs the traceback.
    Mirrors the Telegram webhook's catch-all. More specific handlers above still
    win — FastAPI dispatches by exception type, not registration order.
    """
    logger.exception("Unhandled error in an API request")
    return _error(500, "INTERNAL_ERROR", "Error inesperado. Inténtalo de nuevo.")


def _transaction_id(update: dict) -> UUID:
    """Stable idempotency key for a Telegram update (hard rule 3).

    Telegram redelivers the SAME ``update_id`` when it retries a webhook, so a
    deterministic uuid5 over it means a redelivery hits the pipeline's
    idempotency check (returns the existing row) instead of minting a fresh
    uuid4 and creating a duplicate legal record. The PWA (M4) will instead send
    its own ``crypto.randomUUID()`` per submission.
    """
    return uuid5(_TELEGRAM_NS, str(update["update_id"]))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request, background: BackgroundTasks) -> dict:
    update = await request.json()
    # ACK now; the heavy work (download + Qwen + DB) runs after responding.
    background.add_task(_handle_update, update)
    return {"ok": True}


@app.post("/api/records")
async def create_record(
    audio: UploadFile = File(...),
    transaction_id: UUID = Form(...),
    device_timestamp: datetime = Form(...),
    advisor_id: UUID = Depends(current_advisor_id),
) -> JSONResponse:
    """FLUJO A for the PWA: an audio note -> persisted intervention (spec §7).

    Unlike the Telegram webhook this is SYNCHRONOUS: the advisor's UI waits for
    the outcome (a saved record to list, or a 422 dose/area error to show), so we
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
    advisor_id: UUID = Depends(current_advisor_id),
) -> JSONResponse:
    """The advisor's interventions for the PWA Home list (spec §7).

    Scoped to the authenticated advisor (same dependency as POST). Optional
    ``?state=`` filters by lifecycle; FastAPI validates it against the enum, so a
    bad value is a 422 before this runs. Newest first. No presigned PDF links
    here (one OSS call per row would not scale) — each item carries ``has_pdf``
    and the detail view signs the URL on demand.
    """
    interventions = await container.repository.list_interventions(
        advisor_id, state=state
    )
    return JSONResponse(content=[_record_fields(i) for i in interventions])


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


async def _handle_update(update: dict) -> None:
    """Route the update and apply ONE error policy over the whole processing.

    Runs in a BackgroundTask, so any unhandled error would die silently. Only
    the chat_id extraction lives outside the safety net: without a sender there
    is nobody to reply to, so we just log and drop the update.
    """
    message = update.get("message")
    if not message:
        return
    try:
        chat_id = str(message["from"]["id"])
    except (KeyError, TypeError):
        logger.warning("Update without a usable sender id; dropping it")
        return

    try:
        await _process_message(chat_id, message, _transaction_id(update))
    except DomainError as exc:
        # Spanish, agronomist-readable (the error message is the user feedback).
        await container.notifier.send_message(chat_id, f"⚠️ {exc}")
    except InfrastructureError:
        # A provider failure an adapter translated (Qwen, OSS, ...).
        logger.exception("Infrastructure failure handling Telegram update")
        await container.notifier.send_message(
            chat_id, "❌ Fallo técnico procesando el audio. Inténtalo de nuevo."
        )
    except Exception:
        # Catch-all safety net: covers untranslated errors (raw httpx download,
        # raw Supabase/PostgREST, a KeyError on a weird update) and any
        # unexpected bug. logger.exception writes the full traceback — this is
        # how you actually see *why* it failed.
        logger.exception("Unexpected error handling Telegram update")
        await container.notifier.send_message(
            chat_id, "❌ Error inesperado. Inténtalo de nuevo."
        )


async def _process_message(chat_id: str, message: dict, transaction_id: UUID) -> None:
    """Linear happy path. Any failure here is caught by _handle_update."""
    if "voice" not in message:
        await container.notifier.send_message(
            chat_id, "Envíame una nota de voz con el registro de campo."
        )
        return

    if settings.default_advisor_id is None:
        await container.notifier.send_message(
            chat_id, "Configuración pendiente: falta DEFAULT_ADVISOR_ID."
        )
        return

    # M2 stand-in: device timestamp = Telegram's message date (hard rule 2).
    # transaction_id is derived from the update by the caller (hard rule 3).
    device_timestamp = datetime.fromtimestamp(message["date"], tz=timezone.utc)

    await container.notifier.send_message(chat_id, "🎙️ Audio recibido, procesando…")
    audio = await download_voice(message["voice"]["file_id"])
    intervention = await container.pipeline.register(
        audio=audio,
        advisor_id=settings.default_advisor_id,
        transaction_id=transaction_id,
        device_timestamp=device_timestamp,
    )
    await container.notifier.send_message(chat_id, await _summary(intervention))


def _record_fields(intervention: Intervention) -> dict:
    """Common record fields (sync, NO I/O), shared by the create response and the
    list endpoint.

    A focused projection, NOT the raw entity: internal traceability fields
    (raw_transcription, prompt_version, storage keys) stay out of the API. Field
    names are English (data identifiers); the PWA maps them to Spanish labels.
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
        "created_at": (
            intervention.created_at.isoformat() if intervention.created_at else None
        ),
        "observation": intervention.observation,
        "product_registration_number": intervention.product_registration_number,
        "dose": dose,
        "dose_unit": intervention.dose_unit,
        "target_pest": intervention.target_pest,
        "earliest_harvest_date": (
            intervention.earliest_harvest_date.isoformat()
            if intervention.earliest_harvest_date
            else None
        ),
        "has_pdf": intervention.prescription_pdf_key is not None,
    }


async def _record_response(intervention: Intervention) -> dict:
    """Create-response: the common fields PLUS a best-effort presigned PDF link.

    Signing is per-record I/O, so it lives here (one record) and NOT in the list
    endpoint. A signing failure must NOT turn an already-saved record into an
    error response — we log and return the record without the link.
    """
    data = _record_fields(intervention)
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


async def _summary(intervention: Intervention) -> str:
    """Spanish confirmation of what was persisted."""
    if intervention.lifecycle_state is LifecycleState.OBSERVATION:
        return f"👁️ Observación registrada.\n{intervention.observation or ''}".strip()

    verb = (
        "Prescripción registrada"
        if intervention.lifecycle_state is LifecycleState.PRESCRIBED
        else "Ejecución registrada"
    )
    dose = intervention.applied_dose or intervention.prescribed_dose
    lines = [
        f"✅ {verb}.",
        f"Producto: {intervention.product_registration_number}",
        f"Dosis: {dose} {intervention.dose_unit or ''}".strip(),
        f"Plaga: {intervention.target_pest}",
    ]
    if intervention.earliest_harvest_date:
        lines.append(f"Cosecha no antes de: {intervention.earliest_harvest_date}")

    # Presigned link to the prescription PDF (private bucket, 1h expiry). A
    # signing failure must not swallow the confirmation — the record is saved.
    if intervention.prescription_pdf_key:
        try:
            url = await container.storage.presigned_url(
                intervention.prescription_pdf_key
            )
            lines.append(f"📄 Prescripción (PDF, caduca en 1h): {url}")
        except InfrastructureError:
            # OSS signing failed (expected-ish): just omit the link.
            logger.warning("No se pudo firmar el enlace del PDF (OSS); confirmación sin enlace")
        except Exception:
            # Anything unexpected must NOT turn an already-saved record into an
            # error message: log with traceback and still send the confirmation.
            logger.warning(
                "Error inesperado firmando el enlace del PDF; confirmación sin enlace",
                exc_info=True,
            )
    return "\n".join(lines)
