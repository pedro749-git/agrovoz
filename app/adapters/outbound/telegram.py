import httpx
from app.config.settings import settings

_BASE = "https://api.telegram.org/bot"


async def send_message(chat_id: int, text: str) -> None:
    token = settings.telegram_token.get_secret_value()
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{_BASE}{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10.0,
        )


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