"""Port: speech-to-text over the advisor's field audio."""

from abc import ABC, abstractmethod


class Transcriber(ABC):
    """Turns the dictated audio into raw Spanish text.

    Implementations (today: qwen3-asr-flash via DashScope) must raise
    TranscriptionError on provider failure — never a vendor exception.
    """

    @abstractmethod
    async def transcribe(self, audio: bytes, context: str = "") -> str:
        """audio: the recorded voice-note bytes as received (WebM from the PWA).

        context: optional biasing text — the advisor's own catalog names
        (plots, products, equipment) the recognizer should prefer when it
        hears something close. Empty string = no biasing, plain transcription.
        """
