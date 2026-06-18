"""Inbound FastAPI app (M2).

The Telegram webhook is a thin inbound adapter over the core pipeline: it ACKs
immediately (Telegram retries on timeout), then processes in the background and
pushes the result back through the Notifier port. The future PWA (M4) will be a
second route calling the SAME pipeline — no business logic changes.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid5

from fastapi import BackgroundTasks, FastAPI, Request

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

app = FastAPI(title="GIP Advisor API")


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
