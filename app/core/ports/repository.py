"""Port: persistence of domain entities (today: Supabase/PostgreSQL).

Only the methods FLUJO A (M2) needs — grows on demand per milestone.

Contract notes:
- Lookups return None when not found; the SERVICE decides which domain
  error that becomes (PlotNotFoundError, ProductError...) — the repository
  knows nothing about business rules.
- Every query must filter ``deleted_at IS NULL`` (hard rule 1: legal
  records are soft-deleted, never removed).
- Voice-alias lookups search across ALL the advisor's holdings
  (plots/equipment JOIN holdings ON advisor_id); aliases are unique per
  advisor by design.
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


class Repository(ABC):
    @abstractmethod
    async def get_advisor(self, advisor_id: UUID) -> Advisor | None:
        """For the account_status == ACTIVE check (FLUJO A step 2)."""

    @abstractmethod
    async def get_holding(self, holding_id: UUID) -> Holding | None:
        """The record belongs to the HOLDING (rule 6); needed to render the
        prescription PDF (owner, NIF, REA/REGEPA)."""

    @abstractmethod
    async def get_intervention_by_transaction_id(
        self, transaction_id: UUID
    ) -> Intervention | None:
        """Idempotency (hard rule 3): an existing row means the client
        retried — return it instead of inserting a duplicate."""

    @abstractmethod
    async def get_plot_by_alias(self, advisor_id: UUID, voice_alias: str) -> Plot | None: ...

    @abstractmethod
    async def get_product_by_name(self, trade_name: str) -> Product | None:
        """Lookup in the MAPA vademecum by the trade name the advisor dictated."""

    @abstractmethod
    async def get_equipment_by_alias(
        self, advisor_id: UUID, equipment_alias: str
    ) -> Equipment | None: ...

    @abstractmethod
    async def save_intervention(self, intervention: Intervention) -> Intervention:
        """Insert and return the persisted row (with DB-generated id/timestamps)."""
