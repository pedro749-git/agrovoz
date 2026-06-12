import asyncio
import json
import os
import tempfile

import dashscope
from dashscope import Generation, MultiModalConversation
from pydantic import BaseModel

from app.config.settings import settings

dashscope.api_key = settings.dashscope_api_key.get_secret_value()
dashscope.base_http_api_url = f"{settings.qwen_base_url}/api/v1"

# ── M1 test schema ────────────────────────────────────────────────────────────
# Minimal fields to validate Qwen understands a Spanish field advisor dictation.
# The full legal schema (ExtractedFields per spec §4) starts in M2.

class M1Fields(BaseModel):
    finca: str | None = None          # holding/farm name
    producto: str | None = None       # product name
    dosis: str | None = None          # dose (quantity + unit)
    plaga: str | None = None          # target pest
    equipo: str | None = None         # application equipment
    observaciones: str | None = None  # anything else the advisor mentioned

# ── Extraction prompt ─────────────────────────────────────────────────────────

_EXTRACTION_PROMPT = """\
Eres un asistente técnico de fitosanidad. El usuario te va a dar la transcripción \
de un audio dictado por un asesor GIP en campo. Extrae los campos en JSON estricto \
(sin texto extra, sin markdown). Si un campo no aparece, devuelve null.

Campos a extraer:
- finca: nombre de la explotación o finca
- producto: nombre comercial o materia activa del fitosanitario
- dosis: cantidad y unidad de aplicación (ej. "1.5 litros por hectárea")
- plaga: plaga u organismo objetivo
- equipo: maquinaria o equipo de aplicación
- observaciones: cualquier otra información relevante mencionada

Ejemplos:

Input: "Finca de Pepe, aplicamos Abamectina a 1.5 litros por hectárea contra araña \
roja con el tractor"
Output: {"finca":"Finca de Pepe","producto":"Abamectina","dosis":"1.5 litros por \
hectárea","plaga":"araña roja","equipo":"tractor","observaciones":null}

Input: "Parcela norte de la cooperativa, Clorpirifos dos kilos, trips del olivo, \
mochila pulverizadora, ver si hace falta repetir"
Output: {"finca":"Parcela norte de la cooperativa","producto":"Clorpirifos",\
"dosis":"2 kilos","plaga":"trips del olivo","equipo":"mochila pulverizadora",\
"observaciones":"ver si hace falta repetir"}
"""

# ── Public async API ──────────────────────────────────────────────────────────

# _namefunction is a private sync function that does the actual work.
def _transcribe(tmp_path: str) -> str:
    # MultiModalConversation uploads the local file to DashScope OSS and sets
    # the X-DashScope-OssResourceResolve header so the model can read it back.
    response = MultiModalConversation.call(
        model=settings.qwen_audio_model,
        messages=[{"role": "user", "content": [{"audio": tmp_path}]}],
        result_format="message",
        asr_options={"language": "es", "enable_itn": True},
    )
    if response.status_code != 200:
        raise RuntimeError(f"ASR failed: {response.code} - {response.message}")
    # content is a list of dicts, e.g. [{"text": "..."}]
    content = response.output.choices[0].message.content
    return content[0]["text"] if isinstance(content, list) else content


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Write OGG bytes to a temp file and transcribe via Qwen ASR."""
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        return await asyncio.to_thread(_transcribe, tmp_path)
    finally:
        os.unlink(tmp_path)


def _extract(transcription: str) -> dict:
    response = Generation.call(
        model=settings.qwen_instruct_model,
        messages=[
            {"role": "system", "content": _EXTRACTION_PROMPT},
            {"role": "user", "content": transcription},
        ],
        result_format="message",
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Extraction failed: {response.code} - {response.message}")
    raw = response.output.choices[0].message.content
    return json.loads(raw)


async def extract_fields(transcription: str) -> M1Fields:
    """Run Qwen Instruct over the transcription and return structured M1Fields."""
    raw = await asyncio.to_thread(_extract, transcription)
    return M1Fields(**raw)
