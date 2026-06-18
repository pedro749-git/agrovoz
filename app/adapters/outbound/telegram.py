"""Telegram adapters.

``TelegramNotifier`` implements the Notifier port (the core pushes results
back to the advisor). ``download_voice`` is NOT a port: fetching the audio is
the inbound adapter's job — the core only ever receives bytes.
"""

import logging

import httpx

from app.config.settings import settings
from app.core.ports.notifier import Notifier

logger = logging.getLogger(__name__)

_BASE = "https://api.telegram.org/bot"


class TelegramNotifier(Notifier):
    async def send_message(self, recipient: str, text: str) -> None:
        # Notifications are best-effort: a failed send must NOT break the flow
        # (the legal record is already saved). We log it so it stays visible,
        # but never raise — otherwise an error-path send could mask the real
        # error, or a failed confirmation could look like a failed save.
        token = settings.telegram_token.get_secret_value()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{_BASE}{token}/sendMessage",
                    json={"chat_id": recipient, "text": text},
                    timeout=10.0,
                )
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Telegram sendMessage failed for chat %s: %s", recipient, exc)


async def download_voice(file_id: str) -> bytes:
    """Resolve a Telegram file_id to OGG bytes."""
    token = settings.telegram_token.get_secret_value()
    async with httpx.AsyncClient() as client:
        # Step 1: get the file path on Telegram's servers
        resp = await client.get(
            f"{_BASE}{token}/getFile",
            params={"file_id": file_id},
            timeout=10.0,
        )
        resp.raise_for_status()
        file_path = resp.json()["result"]["file_path"]

        # Step 2: download the actual bytes
        audio = await client.get(
            f"https://api.telegram.org/file/bot{token}/{file_path}",
            timeout=30.0,
        )
        audio.raise_for_status()
        return audio.content
