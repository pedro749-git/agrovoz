"""CorrectionService tests (M8.2) — one per supersede/delete edge case.

Reuses the FLUJO A fakes (same in-memory ports, no Supabase/Qwen). The fake
repo here adds the M8.2 methods and a tiny "DB": one pre-existing PRESCRIBED
row the tests correct/delete. Run:
    uv run pytest tests/test_correction_service.py
"""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.core.domain.errors import DoseError, InterventionNotFoundError
from app.core.domain.models import Intervention
from app.core.domain.schemas import ExtractedFields
from app.core.domain.states import LifecycleState
from app.core.services.correction_service import CorrectionService
from test_registration_pipeline import ADV, HOLD, PLOT, FakeRepo, _pipeline

OLD_ID = uuid4()
DICTATED_AT = datetime(2026, 7, 1, 8, 30, tzinfo=timezone.utc)
CREATED_AT = datetime(2026, 7, 1, 8, 31, tzinfo=timezone.utc)

FIELDS = ExtractedFields(
    record_type="PRESCRIPTION", plot_alias="Finca de Pepe",
    product_name="Abamectina", dose=1.2, target_pest="araña roja",
    equipment_alias="tractor")


class CorrectionFakeRepo(FakeRepo):
    """FakeRepo + the M8.2 methods, over one pre-existing PRESCRIBED row."""

    def __init__(self):
        super().__init__()
        self.old = Intervention(
            transaction_id=uuid4(), lifecycle_state=LifecycleState.PRESCRIBED,
            advisor_id=ADV, holding_id=HOLD, plot_id=PLOT, id=OLD_ID,
            prescription_date=DICTATED_AT, created_at=CREATED_AT,
            prescribed_dose=1.5, raw_transcription="texto dictado original")
        self.soft_deleted = []

    async def get_intervention(self, intervention_id, advisor_id):
        if (intervention_id == self.old.id and advisor_id == self.old.advisor_id
                and self.old.deleted_at is None):
            return self.old
        return None

    async def soft_delete_intervention(self, intervention_id, advisor_id):
        if (intervention_id != self.old.id or advisor_id != self.old.advisor_id
                or self.old.deleted_at is not None):
            return None
        self.old.deleted_at = datetime.now(timezone.utc)
        self.soft_deleted.append(intervention_id)
        return self.old


def _service(repo):
    return CorrectionService(repo, _pipeline(FIELDS, repo))


def test_supersede_replaces_old_record():
    repo = CorrectionFakeRepo()
    replacement = asyncio.run(_service(repo).supersede(
        intervention_id=OLD_ID, fields=FIELDS, advisor_id=ADV,
        transaction_id=uuid4()))
    # New row linked to the old one (rule 7)...
    assert replacement.supersedes_intervention_id == OLD_ID
    assert replacement.prescribed_dose == 1.2
    # ...inheriting the audit trail, the ORIGINAL dictation timestamp (a
    # correction fixes what the record says, not when it happened — rule 2) and
    # the original created_at (keeps its place in lists/campaign periods; the
    # correction moment lives in the old row's deleted_at).
    assert replacement.raw_transcription == "texto dictado original"
    assert replacement.prescription_date == DICTATED_AT
    assert replacement.created_at == CREATED_AT
    # ...and the old row is soft-deleted, never removed (rule 1).
    assert repo.soft_deleted == [OLD_ID]


def test_supersede_leaves_old_intact_when_commit_fails():
    repo = CorrectionFakeRepo()
    bad = FIELDS.model_copy(update={"dose": 99.0})  # above max_allowed_dose
    with pytest.raises(DoseError):
        asyncio.run(_service(repo).supersede(
            intervention_id=OLD_ID, fields=bad, advisor_id=ADV,
            transaction_id=uuid4()))
    # Commit first, soft-delete after: a rejected correction must not lose the
    # original legal record.
    assert repo.soft_deleted == []
    assert repo.old.deleted_at is None


def test_supersede_lost_response_retry_returns_replacement():
    repo = CorrectionFakeRepo()
    service = _service(repo)
    txn = uuid4()
    first = asyncio.run(service.supersede(
        intervention_id=OLD_ID, fields=FIELDS, advisor_id=ADV,
        transaction_id=txn))
    # The response was lost; the PWA retries with the SAME transaction_id. The
    # old row is now soft-deleted (invisible), so without the idempotent replay
    # this would be a misleading 404 for a correction that succeeded.
    repo.existing = first  # commit's transaction_id lookup finds the first row
    retry = asyncio.run(service.supersede(
        intervention_id=OLD_ID, fields=FIELDS, advisor_id=ADV,
        transaction_id=txn))
    assert retry.id == first.id
    assert repo.soft_deleted == [OLD_ID]  # deleted once, not twice


def test_delete_unknown_id_raises_404():
    repo = CorrectionFakeRepo()
    with pytest.raises(InterventionNotFoundError):
        asyncio.run(_service(repo).delete(
            intervention_id=uuid4(), advisor_id=ADV))


def test_delete_soft_deletes():
    repo = CorrectionFakeRepo()
    asyncio.run(_service(repo).delete(intervention_id=OLD_ID, advisor_id=ADV))
    assert repo.soft_deleted == [OLD_ID]
    assert repo.old.deleted_at is not None  # the row still exists (rule 1)
