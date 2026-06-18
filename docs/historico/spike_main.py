"""HISTÓRICO — M1 spike (desechable). NO ejecutable contra el código actual.

Validó que Qwen entiende a un asesor de campo: audio → transcripción → JSON.
Se conserva como artefacto para el capítulo de diseño del TFG. Sus imports
(`transcribe_audio`, `extract_fields`, `send_message`) son las APIs basadas en
funciones de M1, hoy reemplazadas por las clases `QwenTranscriber`/
`QwenExtractor`/`TelegramNotifier`. El flujo real vive en
`app/adapters/inbound/api.py` + `app/core/services/registration_pipeline.py`.
"""

import json

from fastapi import FastAPI, Request, BackgroundTasks

from app.adapters.outbound.qwen import transcribe_audio, extract_fields
from app.adapters.outbound.telegram import send_message, download_voice

app = FastAPI(title="Olek AI Orquestador")


async def process_telegram_update(update: dict) -> None:
    message = update.get("message")
    if not message:
        return

    chat_id = message["from"]["id"]

    if "voice" in message:
        await send_message(chat_id, "Audio recibido, transcribiendo...")
        try:
            audio_bytes = await download_voice(message["voice"]["file_id"])
            transcription = await transcribe_audio(audio_bytes)
            fields = await extract_fields(transcription)

            reply = (
                f"Transcripción:\n{transcription}\n\n"
                f"Campos extraídos:\n{json.dumps(fields.model_dump(), ensure_ascii=False, indent=2)}"
            )
            await send_message(chat_id, reply)
            print(f"[M1] {chat_id} → {fields.model_dump()}")
        except Exception as e:
            print(f"[M1] pipeline error for {chat_id}: {e}")
            await send_message(chat_id, f"Error en el pipeline: {e}")
        return

    if "text" in message:
        await send_message(chat_id, "Envíame un audio de voz para probarlo.")


@app.post("/webhook")
async def telegram_webhook(request: Request, bg_tasks: BackgroundTasks):
    update = await request.json()
    bg_tasks.add_task(process_telegram_update, update)
    return {"status": "ok"}