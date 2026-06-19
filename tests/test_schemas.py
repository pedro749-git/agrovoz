"""Trust-boundary tests (hard rule 4): ExtractedFields validates Qwen's JSON.

Only record_type and plot_alias are always mandatory; the PRESCRIPTION/EXECUTION
fields are optional HERE and enforced later by the pipeline. Run:
    uv run pytest tests/test_schemas.py
"""

import pytest
from pydantic import ValidationError

from app.core.domain.schemas import ExtractedFields


def test_minimal_valid_record():
    f = ExtractedFields(record_type="OBSERVATION", plot_alias="Finca de Pepe")
    # Treatment fields default to None (optional at the schema level).
    assert f.product_name is None and f.dose is None


def test_invalid_record_type_rejected():
    with pytest.raises(ValidationError):
        ExtractedFields(record_type="WHATEVER", plot_alias="Finca de Pepe")


def test_missing_plot_alias_rejected():
    with pytest.raises(ValidationError):
        ExtractedFields(record_type="PRESCRIPTION")
