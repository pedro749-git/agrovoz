"""Port: speech-to-text over the advisor's field audio."""

from abc import ABC, abstractmethod


class Transcriber(ABC):
    """Turns the dictated audio into raw Spanish text.

    Implementations (today: Qwen-Audio via DashScope) must raise
    TranscriptionError on provider failure — never a vendor exception.
    """

    @abstractmethod
    async def transcribe(self, audio: bytes) -> str:
        """audio: the voice file bytes as received (OGG from Telegram)."""
