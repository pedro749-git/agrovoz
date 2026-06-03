import httpx
from app.config import settings

async def send_message(chat_id: int, text: str) -> None:
    """Envía el mensaje procesado de vuelta al usuario en Telegram."""
    url = f"https://api.telegram.org/bot{settings.telegram_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    
    # Un timeout protege tu servidor por si la API de Telegram se cae
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload, timeout=10.0)