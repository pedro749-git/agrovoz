"""Inbound FastAPI app (M2).

The Telegram webhook is a thin inbound adapter over the core pipeline: it ACKs
immediately (Telegram retries on timeout), then processes in the background and
pushes the result back through the Notifier port. The future PWA (M4) will be a
second route calling the SAME pipeline — no business logic changes.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, Request

from app.adapters.outbound.telegram import download_voice
from app.config import container
from app.config.settings import settings
from app.core.domain.errors import DomainError, InfrastructureError
from app.core.domain.models import Intervention
from app.core.domain.states import LifecycleState

app = FastAPI(title="GIP Advisor API")


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
    message = update.get("message")
    if not message:
        return
    chat_id = str(message["from"]["id"])

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

    # M2 stand-in: device timestamp = Telegram's message date (hard rule 2),
    # transaction_id generated here (hard rule 3 says client-generated — the PWA
    # will send crypto.randomUUID(); for the Telegram stand-in we mint it).
    device_timestamp = datetime.fromtimestamp(message["date"], tz=timezone.utc)

    try:
        await container.notifier.send_message(chat_id, "🎙️ Audio recibido, procesando…")
        audio = await download_voice(message["voice"]["file_id"])
        intervention = await container.pipeline.register(
            audio=audio,
            advisor_id=settings.default_advisor_id,
            transaction_id=uuid4(),
            device_timestamp=device_timestamp,
        )
        await container.notifier.send_message(chat_id, _summary(intervention))
    except DomainError as exc:
        # Spanish, agronomist-readable (the error message is the user feedback).
        await container.notifier.send_message(chat_id, f"⚠️ {exc}")
    except InfrastructureError:
        await container.notifier.send_message(
            chat_id, "❌ Fallo técnico procesando el audio. Inténtalo de nuevo."
        )


def _summary(intervention: Intervention) -> str:
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
    return "\n".join(lines)
