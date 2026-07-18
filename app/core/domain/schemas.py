"""Pydantic V2 schemas at the trust boundary (spec §5).

LLM output is untrusted: every Qwen JSON must pass through ExtractedFields
before touching the DB. Missing mandatory field → HTTP 422 with a Spanish
message; never invent values.
"""

from typing import Literal

from pydantic import BaseModel


class ExtractedFields(BaseModel):
    """What the extractor LLM extracts from the audio. The LLM classifies the type."""

    record_type: Literal["OBSERVATION", "PRESCRIPTION", "EXECUTION"]
    plot_alias: str  # mandatory ALWAYS

    # Mandatory if PRESCRIPTION or EXECUTION (enforced in the pipeline):
    product_name: str | None = None
    dose: float | None = None
    dose_unit: str | None = None
    target_pest: str | None = None
    equipment_alias: str | None = None

    # Always optional:
    observation: str | None = None  # if OBSERVATION
    spray_volume_l_ha: float | None = None
    treated_area_ha: float | None = None
    justification: str | None = None
    previous_alternatives: str | None = None
    operator_name: str | None = None
    operator_ropo: str | None = None
    planned_date: str | None = None  # "el viernes", "pasado mañana"
