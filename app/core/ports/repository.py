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
from datetime import date, datetime
from uuid import UUID

from app.core.domain.models import (
    Advisor,
    Equipment,
    Holding,
    Intervention,
    Plot,
    Product,
    Validation,
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
        self,
        advisor_id: UUID,
        *,
        state: LifecycleState | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Intervention]:
        """The advisor's interventions, newest first, optionally filtered by
        lifecycle state (spec §7 GET /api/interventions). Powers the PWA Home
        list (today) and the history screen. ``since``/``until`` are UTC instants
        bounding ``created_at`` as a half-open window ``[since, until)``; either
        may be omitted for an open end. Filters ``deleted_at IS NULL`` like every
        read."""

    @abstractmethod
    async def list_plots_by_ids(self, plot_ids: list[UUID]) -> list[Plot]:
        """Batch lookup for the list projection (each card shows its plot
        alias): the whole list resolves its plots in ONE query over the
        distinct ids, never one query per row. Filters ``deleted_at IS NULL``."""

    @abstractmethod
    async def list_holdings_by_ids(self, holding_ids: list[UUID]) -> list[Holding]:
        """Batch lookup for the list projection (each card shows the holding's
        owner). Same one-query contract as ``list_plots_by_ids``."""

    @abstractmethod
    async def list_products_by_registration_numbers(
        self, registration_numbers: list[str]
    ) -> list[Product]:
        """Batch lookup for the list projection (each card shows the trade name
        instead of the MAPA number). The products catalog is read-only and not
        soft-deleted, so no ``deleted_at`` filter."""

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

    @abstractmethod
    async def soft_delete_intervention(
        self, intervention_id: UUID, advisor_id: UUID
    ) -> Intervention | None:
        """Soft-delete one intervention (M8.2): set ``deleted_at``, never DELETE
        (hard rule 1 — the row stays for the 3-year retention; every read already
        filters it out). Scoped to the advisor like ``get_intervention`` — the
        scope IS the authorization check. Returns the deleted row, or None when
        it does not exist, is not yours, or was already deleted (the caller maps
        that to an indistinguishable 404)."""

    @abstractmethod
    async def list_interventions_in_period(
        self, holding_id: UUID, *, start: date, end: date
    ) -> list[Intervention]:
        """A holding's interventions whose ``created_at`` falls in the civil date
        range [start, end] (inclusive), oldest first — the actuaciones a campaign
        validation covers (FLUJO C, M7). Filters ``deleted_at IS NULL``."""

    @abstractmethod
    async def list_validations(
        self, holding_id: UUID, campaign: str | None = None
    ) -> list[Validation]:
        """A holding's validations, optionally filtered to one campaign. With a
        ``campaign`` (0, 1 or 2 rows: MID_CYCLE / FINAL) the service rejects a
        duplicate type and derives the next period start from the latest
        ``period_end``. Without it (None) returns ALL campaigns — the PWA groups
        them per campaign on the validation screen. Filters ``deleted_at IS NULL``."""

    @abstractmethod
    async def save_validation(self, validation: Validation) -> Validation:
        """Insert and return the persisted campaign validation (FLUJO C, M7)."""

    @abstractmethod
    async def get_validation(
        self, validation_id: UUID, advisor_id: UUID
    ) -> Validation | None:
        """A single validation BY id, scoped to its advisor (PWA PDF link). The
        advisor scope IS the authorization check — you can only open the PDF of
        your own validation. Filters ``deleted_at IS NULL``."""

    @abstractmethod
    async def list_holdings(self, advisor_id: UUID) -> list[Holding]:
        """The advisor's holdings (rule 6: records belong to the holding) — the
        top level of the PWA validation screen. Filters ``deleted_at IS NULL``."""

    @abstractmethod
    async def list_plots(self, holding_id: UUID) -> list[Plot]:
        """A holding's plots — shown under each holding on the validation screen
        so the advisor recognises it. Filters ``deleted_at IS NULL``."""

    # ── ASR biasing context reads (post-M8 hardening) ──
    # Name-only lists (not full entities): the ONLY consumer is the ASR context
    # string handed to Qwen3-ASR-Flash before transcription, and it is built
    # BEFORE anything is resolved — so plots/equipment scope to the ADVISOR
    # (all their holdings), unlike the per-holding lookups above.
    @abstractmethod
    async def list_plot_aliases(self, advisor_id: UUID) -> list[str]:
        """Voice aliases of every plot across the advisor's holdings.
        Filters ``deleted_at IS NULL``."""

    @abstractmethod
    async def list_equipment_aliases(self, advisor_id: UUID) -> list[str]:
        """Voice aliases of every equipment across the advisor's holdings.
        Filters ``deleted_at IS NULL``."""

    @abstractmethod
    async def list_product_names(self) -> list[str]:
        """Trade names of the whole product catalog (read-only MAPA seed, no
        ``deleted_at``). Fine at seed scale; cap/re-scope at vademecum scale."""

    # ── Onboarding writes (hackathon self-signup, TEMPORARY) ──
    # Insert the four entities OnboardingService seeds for a fresh judge. They
    # are generic single-row inserts (an admin alta flow would reuse them), so
    # they can stay even if the hackathon signup is later removed.
    @abstractmethod
    async def save_advisor(self, advisor: Advisor) -> Advisor:
        """Insert and return the persisted advisor (with DB-generated id)."""

    @abstractmethod
    async def save_holding(self, holding: Holding) -> Holding:
        """Insert and return the persisted holding."""

    @abstractmethod
    async def save_plot(self, plot: Plot) -> Plot:
        """Insert and return the persisted plot."""

    @abstractmethod
    async def save_equipment(self, equipment: Equipment) -> Equipment:
        """Insert and return the persisted equipment."""
