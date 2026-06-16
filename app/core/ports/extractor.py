"""Port: structured field extraction from a transcription."""

from abc import ABC, abstractmethod

from app.core.domain.schemas import ExtractedFields


class Extractor(ABC):
    """Turns the raw transcription into validated ExtractedFields.

    The LLM output is untrusted (hard rule 4): implementations must parse
    the provider's JSON through the ExtractedFields Pydantic model — that
    validation is the port's contract, not an extra. Implementations
    (today: Qwen Instruct via DashScope) raise ExtractionError on provider
    failure or on JSON that does not validate.
    """

    @property
    @abstractmethod
    def prompt_version(self) -> str:
        """Version tag of the prompt that produced the extraction. Persisted
        in ``interventions.prompt_version`` for legal traceability (every
        prompt change bumps it, per the methodology)."""

    @abstractmethod
    async def extract(self, transcription: str) -> ExtractedFields: ...
