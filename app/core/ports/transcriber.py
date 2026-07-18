"""Port: speech-to-text over the advisor's field audio."""

from abc import ABC, abstractmethod


class Transcriber(ABC):
    """Turns the dictated audio into raw Spanish text.

    Implementations (today: qwen3-asr-flash via DashScope) must raise
    TranscriptionError on provider failure — never a vendor exception.
    """

    @abstractmethod
    async def transcribe(self, audio: bytes) -> str:
        """audio: the recorded voice-note bytes as received (WebM from the PWA)."""
