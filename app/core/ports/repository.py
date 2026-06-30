"""Port: persistence of domain entities (today: Supabase/PostgreSQL).

Only the methods FLUJO A (M2) needs — grows on demand per milestone.

Contract notes:
- Lookups return None when not found; the SERVICE decides which domain
  error that becomes (PlotNotFoundError, ProductError...) — the repository
  knows nothing about business rules.
- Every query must filter ``deleted_at IS NULL`` (hard rule 1: legal
  records are soft-deleted, never removed).
- Plot voice-alias lookup searches across ALL the advisor's holdings
  (plots JOIN holdings ON advisor_id); plot aliases are unique per advisor.
- Equipment voice-alias lookup is scoped to the HOLDING already resolved
  from the dictated plot, NOT the advisor: two holdings may each have a
  "tractor", and the dictated plot pins which one. Equipment aliases are
  unique per holding (DB partial unique index), not per advisor.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.core.domain.models import (
    Advisor,
    Equipment,
    Holding,
    Intervention,
    Plot,
    Product,
)
from app.core.domain.states import LifecycleState


class Repository(ABC):
    @abstractmethod
    async def get_advisor(self, advisor_id: UUID) -> Advisor | None:
        """For the account_status == ACTIVE check (FLUJO A step 2)."""

    @abstractmethod
    async def get_advisor_by_auth_user_id(
        self, auth_user_id: UUID
    ) -> Advisor | None:
        """Resolve the advisor from a verified Supabase JWT's ``sub`` (M4 auth):
        ``advisors.auth_user_id`` links the row to the ``auth.users`` id."""

    @abstractmethod
    async def list_interventions(
        self, advisor_id: UUID, *, state: LifecycleState | None = None
    ) -> list[Intervention]:
        """The advisor's interventions, newest first, optionally filtered by
        lifecycle state (spec §7 GET /api/interventions). Powers the PWA Home
        list. Filters ``deleted_at IS NULL`` like every read."""

    @abstractmethod
    async def get_holding(self, holding_id: UUID) -> Holding | None:
        """The record belongs to the HOLDING (rule 6); needed to render the
        prescription PDF (owner, NIF, REA/REGEPA)."""

    @abstractmethod
    async def get_intervention(
        self, intervention_id: UUID, advisor_id: UUID
    ) -> Intervention | None:
        """A single intervention BY id, scoped to its advisor (PWA PDF link).
        Scoping by advisor is the authorization check — you can only sign the
        PDF of your own record. Filters ``deleted_at IS NULL`` like every read."""

    @abstractmethod
    async def get_intervention_by_transaction_id(
        self, transaction_id: UUID
    ) -> Intervention | None:
        """Idempotency (hard rule 3): an existing row means the client
        retried — return it instead of inserting a duplicate."""

    @abstractmethod
    async def get_plot_by_alias(self, advisor_id: UUID, voice_alias: str) -> Plot | None: ...

    @abstractmethod
    async def get_plot(self, plot_id: UUID) -> Plot | None:
        """A single plot BY id — FLUJO B (M5) re-validates the real treated area
        against ``plot.enclosure_area_ha`` (hard rule 5)."""

    @abstractmethod
    async def get_product_by_name(self, trade_name: str) -> Product | None:
        """Lookup in the MAPA vademecum by the trade name the advisor dictated."""

    @abstractmethod
    async def get_product_by_registration_number(
        self, registration_number: str
    ) -> Product | None:
        """Lookup by the MAPA registration number stored on the intervention —
        FLUJO B (M5) re-validates the real dose against ``max_allowed_dose``."""

    @abstractmethod
    async def get_equipment_by_alias(
        self, holding_id: UUID, equipment_alias: str
    ) -> Equipment | None:
        """Resolve the dictated equipment alias WITHIN one holding (the one the
        plot belongs to). Scoping to the holding — not the advisor — lets two
        holdings each keep a "tractor" without colliding."""

    @abstractmethod
    async def get_equipment(self, equipment_id: UUID) -> Equipment | None:
        """A single equipment BY id — FLUJO B (M5) reads its
        ``iteaf_inspection_date`` to flag an expired inspection (rule: ITEAF is
        mandatory and periodic). Filters ``deleted_at IS NULL`` like every read."""

    @abstractmethod
    async def save_intervention(self, intervention: Intervention) -> Intervention:
        """Insert and return the persisted row (with DB-generated id/timestamps)."""

    @abstractmethod
    async def update_intervention(self, intervention: Intervention) -> Intervention:
        """Persist changes to an existing intervention (matched by id) and return
        the updated row. FLUJO B (M5): PRESCRIBED -> EXECUTED."""
