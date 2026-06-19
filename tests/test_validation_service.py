"""Legal validation tests (spec §4, hard rule 5) — happy path + each violation.

Pure domain logic, no I/O: the pipeline resolves the rows and hands them here.
Run: uv run pytest tests/test_validation_service.py
"""

from uuid import uuid4

import pytest

from app.core.domain.errors import AreaError, DoseError, ProductError
from app.core.domain.models import Plot, Product
from app.core.domain.schemas import ExtractedFields
from app.core.services.validation_service import validate_registration


def _plot(area=5.0):
    return Plot(holding_id=uuid4(), voice_alias="Finca de Pepe", crop="Limonero",
                enclosure_area_ha=area, sigpac_province="30",
                sigpac_municipality="001", sigpac_polygon="1",
                sigpac_parcel="1", sigpac_enclosure="1")


def _product(authorized=True, max_dose=1.5):
    return Product(registration_number="ES-1", trade_name="Abamectina",
                   active_substance="abamectina", authorized=authorized,
                   max_allowed_dose=max_dose, dose_unit="L/ha")


def _fields(**kw):
    base = dict(record_type="PRESCRIPTION", plot_alias="Finca de Pepe",
                product_name="Abamectina", dose=1.0, dose_unit="L/ha",
                target_pest="araña roja", equipment_alias="tractor")
    base.update(kw)
    return ExtractedFields(**base)


def test_legal_prescription_passes():
    # Dose within the legal max, no area given -> nothing raises.
    validate_registration(_fields(dose=1.5), _plot(), _product())


def test_observation_has_no_product_to_validate():
    validate_registration(
        ExtractedFields(record_type="OBSERVATION", plot_alias="Finca de Pepe"),
        _plot(), None)


def test_dose_above_max_raises():
    with pytest.raises(DoseError):
        validate_registration(_fields(dose=1.6), _plot(), _product(max_dose=1.5))


def test_unauthorized_product_raises():
    with pytest.raises(ProductError):
        validate_registration(_fields(), _plot(), _product(authorized=False))


def test_area_above_enclosure_raises():
    with pytest.raises(AreaError):
        validate_registration(_fields(treated_area_ha=6.0), _plot(area=5.0), _product())


def test_limits_are_inclusive():
    # dose == max and area == enclosure are LEGAL (the rule is >, not >=).
    validate_registration(_fields(dose=1.5, treated_area_ha=5.0),
                          _plot(area=5.0), _product(max_dose=1.5))
