"""Qwen adapters (DashScope): speech-to-text + field extraction.

Implements the Transcriber and Extractor ports. The DashScope SDK is sync and
blocking, so the actual calls run in a worker thread (``asyncio.to_thread``)
to avoid blocking the event loop. Vendor failures are translated into the
core's infrastructure errors (hard rule: the core never sees a DashScope
exception).
"""

import asyncio
import json
from pathlib import Path

import dashscope
from dashscope import Generation, MultiModalConversation
from pydantic import ValidationError

from app.config.settings import settings
from app.core.domain.errors import ExtractionError, TranscriptionError
from app.core.domain.schemas import ExtractedFields
from app.core.ports.extractor import Extractor
from app.core.ports.transcriber import Transcriber

dashscope.api_key = settings.dashscope_api_key.get_secret_value()
dashscope.base_http_api_url = f"{settings.qwen_base_url}/api/v1"

# The extraction prompt lives in a versioned file (methodology: every change
# bumps the version, persisted in interventions.prompt_version).
PROMPT_VERSION = "v2"
_PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "extraction_v2.md"
_EXTRACTION_PROMPT = _PROMPT_PATH.read_text(encoding="utf-8")


class QwenTranscriber(Transcriber):
    """qwen3-asr-flash (ASR) over the advisor's field audio."""

    async def transcribe(self, audio: bytes, context: str = "") -> str:
        return await asyncio.to_thread(self._transcribe, audio, context)

    @staticmethod
    def _transcribe(audio: bytes, context: str) -> str:
        # MultiModalConversation reads a data URI; we hand it the raw OGG bytes
        # base64-encoded so we never touch the local filesystem.
        import base64

        b64 = base64.b64encode(audio).decode("ascii")
        # Qwen3-ASR-Flash context enhancement: free text in the system message
        # biases recognition toward these names (the advisor's catalog). With no
        # context the call is exactly the pre-biasing one.
        messages: list[dict] = []
        if context:
            messages.append({"role": "system", "content": [{"text": context}]})
        messages.append(
            {"role": "user", "content": [{"audio": f"data:audio/ogg;base64,{b64}"}]}
        )
        try:
            response = MultiModalConversation.call(
                model=settings.qwen_audio_model,
                messages=messages,
                result_format="message",
                asr_options={"language": "es", "enable_itn": True},
                request_timeout=settings.vendor_timeout_seconds,
            )
        except Exception as exc:  # vendor/network failure
            raise TranscriptionError(str(exc)) from exc

        if response.status_code != 200:
            raise TranscriptionError(f"{response.code} - {response.message}")

        content = response.output.choices[0].message.content
        text = content[0]["text"] if isinstance(content, list) else content
        if not text or not text.strip():
            raise TranscriptionError("empty transcription")
        return text.strip()


class QwenExtractor(Extractor):
    """qwen-flash: transcription -> validated ExtractedFields."""

    @property
    def prompt_version(self) -> str:
        return PROMPT_VERSION

    async def extract(self, transcription: str) -> ExtractedFields:
        raw = await asyncio.to_thread(self._extract, transcription)
        try:
            # Hard rule 4: LLM output is untrusted -> Pydantic at the boundary.
            return ExtractedFields(**raw)
        except ValidationError as exc:
            raise ExtractionError(f"LLM JSON did not validate: {exc}") from exc

    @staticmethod
    def _extract(transcription: str) -> dict:
        try:
            response = Generation.call(
                model=settings.qwen_instruct_model,
                messages=[
                    {"role": "system", "content": _EXTRACTION_PROMPT},
                    {"role": "user", "content": transcription},
                ],
                result_format="message",
                response_format={"type": "json_object"},
                temperature=0.1,
                request_timeout=settings.vendor_timeout_seconds,
            )
        except Exception as exc:
            raise ExtractionError(str(exc)) from exc

        if response.status_code != 200:
            raise ExtractionError(f"{response.code} - {response.message}")

        raw = response.output.choices[0].message.content
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"LLM returned non-JSON: {raw[:200]}") from exc
