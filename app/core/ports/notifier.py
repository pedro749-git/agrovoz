"""Port: outbound messages to the advisor.

The pipeline runs in the background (the webhook ACKs immediately), so the
core needs a way to push the result back ("👁️ Observación registrada...",
legal-validation errors in Spanish...). Today that channel is the Telegram
bot; in M4+ it may become PWA push — the core only knows "notify".

Note: downloading the voice file is NOT a port. Fetching the audio from
Telegram is the inbound adapter's job; the core receives bytes.
"""

from abc import ABC, abstractmethod


class Notifier(ABC):
    @abstractmethod
    async def send_message(self, recipient: str, text: str) -> None:
        """recipient: channel-specific id (Telegram chat_id today).
        text: user-facing, ALWAYS in Spanish."""
