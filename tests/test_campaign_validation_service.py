"""CampaignValidationService tests (M7) — one per FLUJO C edge case.

In-memory fake repository, so it never touches Supabase. Async bodies run via
asyncio.run (no pytest-asyncio, matching the other service tests).
Run:
    uv run pytest tests/test_campaign_validation_service.py
"""

import asyncio
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from app.core.domain.errors import (
    HoldingNotFoundError,
    InvalidCampaignError,
    RemarksRequiredError,
    ValidationExistsError,
)
from app.core.domain.models import (
    Advisor,
    Holding,
    Intervention,
    Validation,
    ValidationType,
)
from app.core.domain.states import LifecycleState
from app.core.services.campaign_validation_service import CampaignValidationService

ADV = UUID("11111111-1111-1111-1111-111111111111")
OTHER_ADV = UUID("22222222-2222-2222-2222-222222222222")
HOLD = uuid4()
CAMPAIGN = "2026"
SIGNED_AT = datetime(2026, 6, 30, 10, 0, tzinfo=timezone.utc)
ADVISOR = Advisor(
    full_name="Ana Asesora", dni="00000000T", ropo_number="ROPO-1", id=ADV
)


def _holding(**overrides) -> Holding:
    base = dict(
        advisor_id=ADV,
        owner_name="Pepe",
        owner_nif="12345678Z",
        rea_regepa_number="REA-1",
        id=HOLD,
    )
    base.update(overrides)
    return Holding(**base)


def _intervention() -> Intervention:
    return Intervention(
        transaction_id=uuid4(),
        lifecycle_state=LifecycleState.EXECUTED,
        advisor_id=ADV,
        holding_id=HOLD,
        plot_id=uuid4(),
    )


def _existing_validation(**overrides) -> Validation:
    base = dict(
        advisor_id=ADV,
        holding_id=HOLD,
        campaign=CAMPAIGN,
        type=ValidationType.MID_CYCLE,
        validation_date=datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc),
        conformity=True,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 4, 1),
        intervention_count=2,
        id=uuid4(),
    )
    base.update(overrides)
    return Validation(**base)


class FakeRepo:
    """Only the methods validate_campaign touches."""

    def __init__(
        self,
        holding: Holding | None,
        *,
        validations: list[Validation] | None = None,
        interventions: list[Intervention] | None = None,
        advisor: Advisor | None = ADVISOR,
    ):
        self._holding = holding
        self._validations = validations or []
        self._interventions = interventions or []
        self._advisor = advisor
        self.saved: Validation | None = None
        self.period_asked: tuple[date, date] | None = None

    async def get_holding(self, holding_id):
        return self._holding

    async def get_advisor(self, advisor_id):
        return self._advisor

    async def list_validations(self, holding_id, campaign):
        return self._validations

    async def list_interventions_in_period(self, holding_id, *, start, end):
        self.period_asked = (start, end)
        return self._interventions

    async def save_validation(self, validation):
        validation.id = uuid4()
        self.saved = validation
        return validation


class FakePdf:
    """Records the validation it was asked to render; returns dummy PDF bytes."""

    def __init__(self):
        self.called_with: Validation | None = None

    def generate_validation(self, *, validation, advisor, holding):
        self.called_with = validation
        return b"%PDF-1.4 fake"


class FakeStorage:
    """Records uploads; can be told to fail to exercise the best-effort path."""

    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.uploaded_key: str | None = None

    async def upload(self, *, data, key, content_type):
        if self.fail:
            raise RuntimeError("OSS down")
        self.uploaded_key = key


def _validate(repo, *, pdf=None, storage=None, **kwargs):
    service = CampaignValidationService(
        repo, pdf or FakePdf(), storage or FakeStorage()
    )
    params = dict(
        holding_id=HOLD,
        advisor_id=ADV,
        campaign=CAMPAIGN,
        validation_type=ValidationType.MID_CYCLE,
        conformity=True,
        validation_date=SIGNED_AT,
    )
    params.update(kwargs)
    return asyncio.run(service.validate_campaign(**params))


def test_first_validation_covers_from_campaign_start():
    # No previous validation -> period starts on Jan 1st of the campaign year and
    # ends on the signing date; the intervention count is stored on the record.
    repo = FakeRepo(_holding(), interventions=[_intervention(), _intervention()])
    result = _validate(repo)

    assert result.period_start == date(2026, 1, 1)
    assert result.period_end == date(2026, 6, 30)
    assert result.intervention_count == 2
    assert result.type is ValidationType.MID_CYCLE
    assert repo.saved is result
    assert repo.period_asked == (date(2026, 1, 1), date(2026, 6, 30))


def test_second_validation_starts_after_previous_period():
    # A FINAL after an existing MID_CYCLE starts the day AFTER the previous
    # period_end (no gap, no overlap).
    repo = FakeRepo(_holding(), validations=[_existing_validation()])
    result = _validate(repo, validation_type=ValidationType.FINAL)

    assert result.period_start == date(2026, 4, 2)  # 2026-04-01 + 1 day
    assert result.period_end == date(2026, 6, 30)
    assert result.type is ValidationType.FINAL


def test_duplicate_type_is_rejected():
    # The same type twice in a campaign is not allowed (UNIQUE holding+campaign+type).
    repo = FakeRepo(_holding(), validations=[_existing_validation()])
    with pytest.raises(ValidationExistsError):
        _validate(repo, validation_type=ValidationType.MID_CYCLE)
    assert repo.saved is None


def test_non_conform_without_remarks_is_rejected():
    repo = FakeRepo(_holding())
    with pytest.raises(RemarksRequiredError):
        _validate(repo, conformity=False)
    assert repo.saved is None


def test_non_conform_with_remarks_is_saved():
    repo = FakeRepo(_holding())
    result = _validate(repo, conformity=False, remarks="Dosis fuera de rango en 2 registros")
    assert result.conformity is False
    assert result.remarks == "Dosis fuera de rango en 2 registros"


def test_blank_remarks_stored_as_none():
    # Whitespace is not a real remark -> normalised to None (conform, so allowed).
    repo = FakeRepo(_holding())
    result = _validate(repo, remarks="   ")
    assert result.remarks is None


def test_foreign_holding_is_not_found():
    # A holding managed by another advisor is an indistinguishable 404.
    repo = FakeRepo(_holding(advisor_id=OTHER_ADV))
    with pytest.raises(HoldingNotFoundError):
        _validate(repo)
    assert repo.saved is None


def test_unknown_holding_is_not_found():
    repo = FakeRepo(None)
    with pytest.raises(HoldingNotFoundError):
        _validate(repo)


def test_malformed_campaign_is_rejected():
    # A campaign label with no leading 4-digit year cannot derive a period start.
    repo = FakeRepo(_holding())
    with pytest.raises(InvalidCampaignError):
        _validate(repo, campaign="campaña")
    assert repo.saved is None


def test_pdf_rendered_uploaded_and_key_set():
    # The signed PDF is rendered, uploaded, and its deterministic key is on the
    # saved row (single INSERT, no follow-up update).
    repo = FakeRepo(_holding())
    pdf, storage = FakePdf(), FakeStorage()
    result = _validate(repo, pdf=pdf, storage=storage)

    expected_key = f"validations/{HOLD}_{CAMPAIGN}_MID_CYCLE.pdf"
    assert pdf.called_with is result  # rendered from the built validation
    assert storage.uploaded_key == expected_key
    assert result.validation_pdf_key == expected_key


def test_pdf_upload_failure_is_best_effort():
    # A storage failure must NOT block the signing: the validation is saved with
    # no key (the PDF is regenerable from the row).
    repo = FakeRepo(_holding())
    result = _validate(repo, storage=FakeStorage(fail=True))

    assert result.validation_pdf_key is None
    assert repo.saved is result  # still persisted
