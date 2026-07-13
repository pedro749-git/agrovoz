"""Correction + deletion of interventions (M8.2, hard rules 1/7).

A legal record is never edited in place and never removed:
- Deletion = soft-delete (set ``deleted_at``; the row stays for the 3-year
  retention and every read already filters it out).
- Correction = SUPERSEDE: insert a replacement row (through the same
  ``pipeline.commit`` as FLUJO A, so the edited fields pass the full legal
  validation again) pointing at the old record via
  ``supersedes_intervention_id``, then soft-delete the old one. The link is
  what makes a correction distinguishable from a plain deletion in the data.

Order matters in ``supersede``: commit FIRST, soft-delete AFTER. If the
commit fails (a 422 dose/area error on the edited fields), the old record is
untouched; if the soft-delete fails after a successful commit, the retry
re-enters commit, hits the idempotent transaction_id path, and re-runs only
the missing soft-delete — the flow self-heals instead of losing the record.
"""

from datetime import datetime
from uuid import UUID

from app.core.domain.errors import InterventionNotFoundError
from app.core.domain.models import Intervention
from app.core.domain.schemas import ExtractedFields
from app.core.ports.repository import Repository
from app.core.services.registration_pipeline import RegistrationPipeline


class CorrectionService:
    def __init__(self, repository: Repository, pipeline: RegistrationPipeline) -> None:
        self._repo = repository
        self._pipeline = pipeline

    async def delete(self, *, intervention_id: UUID, advisor_id: UUID) -> None:
        """Soft-delete one record. Scoped to the advisor (the scope IS the
        authorization), so unknown, foreign and already-deleted ids are the same
        indistinguishable 404."""
        deleted = await self._repo.soft_delete_intervention(
            intervention_id, advisor_id
        )
        if deleted is None:
            raise InterventionNotFoundError("No encuentro ese registro.")

    async def supersede(
        self,
        *,
        intervention_id: UUID,
        fields: ExtractedFields,
        advisor_id: UUID,
        transaction_id: UUID,
    ) -> Intervention:
        """Replace a record with a corrected one (new row + soft-delete, rule 7).

        The replacement inherits from the old record its transcription (the
        audit trail documents what was DICTATED, and a correction edits fields,
        not the audio), its ORIGINAL device timestamp (the correction fixes what
        the record says, not when the field event happened — hard rule 2) and
        its ``created_at`` (so it keeps the original's place in the today/history
        lists and campaign validation periods; the correction moment itself is
        recorded by the old row's ``deleted_at``). The client sends only the
        edited fields and a fresh ``transaction_id``.
        """
        old = await self._repo.get_intervention(intervention_id, advisor_id)
        if old is None:
            # Lost-response retry: the correction may have already run (the old
            # row is soft-deleted, the replacement saved under this same
            # transaction_id). Return the replacement — that is what
            # idempotency promises (rule 3) — instead of a misleading 404.
            existing = await self._repo.get_intervention_by_transaction_id(
                transaction_id
            )
            if existing is not None and existing.advisor_id == advisor_id:
                return existing
            raise InterventionNotFoundError("No encuentro ese registro.")

        replacement = await self._pipeline.commit(
            fields=fields,
            advisor_id=advisor_id,
            transaction_id=transaction_id,
            device_timestamp=self._original_timestamp(old),
            transcription=old.raw_transcription or "",
            supersedes=old.id,
            created_at=old.created_at,
        )
        await self._repo.soft_delete_intervention(old.id, advisor_id)
        return replacement

    @staticmethod
    def _original_timestamp(old: Intervention) -> datetime:
        """The moment the corrected record documents: the original dictation's
        device timestamp (prescription_date, or treatment_date for a record that
        went straight to EXECUTED). OBSERVATIONs carry neither — commit does not
        use the timestamp for them — so created_at is a safe last resort."""
        return old.prescription_date or old.treatment_date or old.created_at
