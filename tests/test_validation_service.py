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


def test_dose_in_hl_is_converted_before_comparing():
    # 0.5 hl/ha IS 50 L/ha: must be blocked against a 1.5 L/ha max even though
    # the raw number (0.5) is below it — the original unit-blindness bug.
    with pytest.raises(DoseError):
        validate_registration(_fields(dose=0.5, dose_unit="hl/ha"),
                              _plot(), _product(max_dose=1.5))


def test_dose_in_ml_within_max_passes():
    # 1500 ml/ha == 1.5 L/ha == the max: legal, must NOT be rejected.
    validate_registration(_fields(dose=1500, dose_unit="ml/ha"),
                          _plot(), _product(max_dose=1.5))


def test_dictation_spelling_of_the_unit_is_understood():
    # Qwen may echo the spoken form instead of the compact one.
    validate_registration(_fields(dose=1.5, dose_unit="litros por hectárea"),
                          _plot(), _product(max_dose=1.5))


def test_unrecognized_unit_is_blocked():
    # The app cannot certify a dose it cannot compare (hard rule 5): an unknown
    # unit against a known catalog unit refuses to persist rather than guess.
    with pytest.raises(DoseError):
        validate_registration(_fields(dose=1.0, dose_unit="L/árbol"),
                              _plot(), _product())


def test_incomparable_denominators_are_blocked():
    # cc/hl doses the spray mix; comparing with an L/ha max needs the spray
    # volume -> not certifiable -> blocked.
    with pytest.raises(DoseError):
        validate_registration(_fields(dose=30, dose_unit="cc/hl"),
                              _plot(), _product())


def test_mass_dose_against_volume_max_is_blocked():
    # Kg/ha against an L/ha catalog max: different dimensions, not comparable.
    with pytest.raises(DoseError):
        validate_registration(_fields(dose=1.0, dose_unit="Kg/ha"),
                              _plot(), _product())


def test_missing_unit_keeps_numeric_comparison():
    # No dictated unit: assume the catalog's one (previous behavior).
    validate_registration(_fields(dose=1.5, dose_unit=None),
                          _plot(), _product(max_dose=1.5))
    with pytest.raises(DoseError):
        validate_registration(_fields(dose=1.6, dose_unit=None),
                              _plot(), _product(max_dose=1.5))
