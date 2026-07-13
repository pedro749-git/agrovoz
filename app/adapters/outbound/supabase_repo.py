"""Supabase adapter implementing the Repository port.

Uses the service_role key, which bypasses RLS — the inbound is the trusted
backend that has already verified the advisor's Supabase JWT. The RLS policies
in the migration back the PWA path (M4+), where each advisor authenticates with
an email OTP code or password.

Every read filters ``deleted_at IS NULL`` (hard rule 1: soft-delete only).
"""

import dataclasses
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import get_args, get_type_hints
from uuid import UUID

from postgrest.exceptions import APIError
from supabase import AsyncClient, create_async_client

from app.adapters.outbound._fuzzy import best_match
from app.config.settings import settings
from app.core.domain.errors import RepositoryError
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
from app.core.ports.repository import Repository

_client: AsyncClient | None = None

# Postgres SQLSTATE for a UNIQUE constraint violation (used for the idempotency
# race in save_intervention).
_UNIQUE_VIOLATION = "23505"


async def get_client() -> AsyncClient:
    """Create the async Supabase client once and reuse it (singleton)."""
    global _client
    if _client is None:
        _client = await create_async_client(
            settings.supabase_url,
            settings.supabase_service_key.get_secret_value(),
        )
    return _client


async def _run(query):
    """Execute a PostgREST query, translating transport/DB failures.

    Every read/write awaits ``.execute()`` here so a raw PostgREST ``APIError``
    or an httpx network error becomes a port-level ``RepositoryError`` (inbound
    -> 503), instead of leaking to the catch-all 500. Deserialization stays at
    the call site on purpose: a mapping bug is a real 500, not infrastructure.
    """
    try:
        return await query.execute()
    except APIError as exc:
        raise RepositoryError(f"Supabase/PostgREST error: {exc}") from exc
    except Exception as exc:  # httpx network failure, timeout, ...
        raise RepositoryError(f"Database call failed: {exc}") from exc


# ── (De)serialization helpers ───────────────────────────────────────────────
# Supabase returns/accepts JSON primitives; the domain uses UUID/datetime/date/
# Enum. These two helpers coerce both ways using the dataclass type hints, so we
# don't hand-write a mapper per entity.

def _coerce(value, hint):
    if value is None:
        return None
    # Unwrap Optional[X] / X | None down to the concrete type.
    args = [a for a in get_args(hint) if a is not type(None)]
    target = args[0] if args else hint
    if target is UUID:
        return UUID(value)
    if target is datetime:
        return datetime.fromisoformat(value)
    if target is date:
        return date.fromisoformat(value)
    if isinstance(target, type) and issubclass(target, Enum):
        return target(value)
    return value


def _deserialize(cls, row: dict):
    """Build a domain dataclass from a DB row (extra row keys are ignored)."""
    hints = get_type_hints(cls)
    return cls(**{
        f.name: _coerce(row[f.name], hints[f.name])
        for f in dataclasses.fields(cls)
        if f.name in row
    })


def _to_json(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


# Columns the DB fills in itself — never sent on insert.
_DB_GENERATED = ("id", "created_at", "updated_at")


def _serialize(obj) -> dict:
    """Domain dataclass -> insert payload, with ONLY real table columns.

    We do not blindly dump every field: that breaks the day a model gains a
    field that is not a column (the INSERT fails with an opaque PostgREST
    error, hard to trace). Instead we skip the DB-generated columns and any
    field explicitly tagged ``field(metadata={"persist": False})`` — the
    documented escape hatch for computed/in-memory-only fields.
    ``tests/test_serialize_columns.py`` asserts this payload matches the
    migration's columns exactly, so model<->schema drift fails loudly there.

    Exception: an explicitly SET ``created_at`` is sent (overriding the DB
    default). A correction (M8.2) inherits its predecessor's created_at so the
    replacement keeps the original's place everywhere created_at drives
    (today/history lists, campaign validation periods); the moment of the
    correction itself survives in the old row's ``deleted_at``.
    """
    persisted = {
        f.name
        for f in dataclasses.fields(obj)
        if f.name not in _DB_GENERATED and f.metadata.get("persist", True)
    }
    payload = {
        k: _to_json(v)
        for k, v in dataclasses.asdict(obj).items()
        if k in persisted
    }
    if getattr(obj, "created_at", None) is not None:
        payload["created_at"] = _to_json(obj.created_at)
    return payload


class SupabaseRepository(Repository):
    async def get_advisor(self, advisor_id: UUID) -> Advisor | None:
        client = await get_client()
        res = await _run(
            client.table("advisors")
            .select("*")
            .eq("id", str(advisor_id))
            .is_("deleted_at", "null")
            .limit(1)
        )
        return _deserialize(Advisor, res.data[0]) if res.data else None

    async def get_advisor_by_auth_user_id(
        self, auth_user_id: UUID
    ) -> Advisor | None:
        client = await get_client()
        res = await _run(
            client.table("advisors")
            .select("*")
            .eq("auth_user_id", str(auth_user_id))
            .is_("deleted_at", "null")
            .limit(1)
        )
        return _deserialize(Advisor, res.data[0]) if res.data else None

    async def list_interventions(
        self,
        advisor_id: UUID,
        *,
        state: LifecycleState | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[Intervention]:
        client = await get_client()
        query = (
            client.table("interventions")
            .select("*")
            .eq("advisor_id", str(advisor_id))
            .is_("deleted_at", "null")
        )
        if state is not None:
            query = query.eq("lifecycle_state", state.value)
        # created_at is a UTC timestamp; since/until are the UTC instants the
        # inbound layer computed from the advisor's civil-day range. Half-open
        # [since, until) so a day-boundary record is never double-counted.
        if since is not None:
            query = query.gte("created_at", since.isoformat())
        if until is not None:
            query = query.lt("created_at", until.isoformat())
        # 500 (not 100) so a full season's history is not silently truncated; a
        # single advisor's yearly volume stays well under this. Paginate if that
        # ever stops holding.
        res = await _run(query.order("created_at", desc=True).limit(500))
        return [_deserialize(Intervention, row) for row in res.data]

    async def get_holding(self, holding_id: UUID) -> Holding | None:
        client = await get_client()
        res = await _run(
            client.table("holdings")
            .select("*")
            .eq("id", str(holding_id))
            .is_("deleted_at", "null")
            .limit(1)
        )
        return _deserialize(Holding, res.data[0]) if res.data else None

    async def get_intervention(
        self, intervention_id: UUID, advisor_id: UUID
    ) -> Intervention | None:
        client = await get_client()
        res = await _run(
            client.table("interventions")
            .select("*")
            .eq("id", str(intervention_id))
            .eq("advisor_id", str(advisor_id))  # scope = authorization
            .is_("deleted_at", "null")
            .limit(1)
        )
        return _deserialize(Intervention, res.data[0]) if res.data else None

    async def get_intervention_by_transaction_id(
        self, transaction_id: UUID
    ) -> Intervention | None:
        client = await get_client()
        res = await _run(
            client.table("interventions")
            .select("*")
            .eq("transaction_id", str(transaction_id))
            .is_("deleted_at", "null")
            .limit(1)
        )
        return _deserialize(Intervention, res.data[0]) if res.data else None

    async def get_plot_by_alias(self, advisor_id: UUID, voice_alias: str) -> Plot | None:
        client = await get_client()
        # Fetch the advisor's plots (few) and fuzzy-match the dictated alias
        # against the real rows — the ASR mis-hears proper nouns.
        res = await _run(
            client.table("plots")
            .select("*, holdings!inner(advisor_id)")
            .eq("holdings.advisor_id", str(advisor_id))
            .is_("deleted_at", "null")
        )
        row = best_match(voice_alias, res.data, "voice_alias")
        return _deserialize(Plot, row) if row else None

    async def get_plot(self, plot_id: UUID) -> Plot | None:
        client = await get_client()
        res = await _run(
            client.table("plots")
            .select("*")
            .eq("id", str(plot_id))
            .is_("deleted_at", "null")
            .limit(1)
        )
        return _deserialize(Plot, res.data[0]) if res.data else None

    async def get_product_by_name(self, trade_name: str) -> Product | None:
        client = await get_client()
        # M2: fuzzy-match over the (small) seeded catalog. At vademecum scale
        # (thousands), replace this full fetch with a pg_trgm similarity query.
        # No authorized filter here: an unauthorized hit still resolves, so the
        # validation service can raise the precise "not authorized" error.
        res = await _run(client.table("products").select("*"))
        row = best_match(trade_name, res.data, "trade_name")
        return _deserialize(Product, row) if row else None

    async def get_product_by_registration_number(
        self, registration_number: str
    ) -> Product | None:
        # Exact lookup by natural PK (no fuzzy match, no deleted_at: the
        # products catalog is read-only and not soft-deleted).
        client = await get_client()
        res = await _run(
            client.table("products")
            .select("*")
            .eq("registration_number", registration_number)
            .limit(1)
        )
        return _deserialize(Product, res.data[0]) if res.data else None

    async def get_equipment_by_alias(
        self, holding_id: UUID, equipment_alias: str
    ) -> Equipment | None:
        # Scoped to the holding (resolved from the dictated plot), so two
        # holdings can each have a "tractor" without the fuzzy match seeing both.
        client = await get_client()
        res = await _run(
            client.table("equipment")
            .select("*")
            .eq("holding_id", str(holding_id))
            .is_("deleted_at", "null")
        )
        row = best_match(equipment_alias, res.data, "equipment_alias")
        return _deserialize(Equipment, row) if row else None

    async def get_equipment(self, equipment_id: UUID) -> Equipment | None:
        client = await get_client()
        res = await _run(
            client.table("equipment")
            .select("*")
            .eq("id", str(equipment_id))
            .is_("deleted_at", "null")
            .limit(1)
        )
        return _deserialize(Equipment, res.data[0]) if res.data else None

    async def save_intervention(self, intervention: Intervention) -> Intervention:
        client = await get_client()
        insert = client.table("interventions").insert(_serialize(intervention))
        try:
            res = await insert.execute()
        except APIError as exc:
            # TOCTOU idempotency (hard rule 3): the pipeline pre-checks
            # transaction_id, but two concurrent requests can both pass that
            # check and INSERT. The UNIQUE(transaction_id) constraint rejects the
            # loser; rather than surface a 503, return the row the winner saved —
            # which is exactly what idempotency promises. Any OTHER unique
            # violation finds no such row and re-raises as a real RepositoryError.
            if exc.code == _UNIQUE_VIOLATION:
                existing = await self.get_intervention_by_transaction_id(
                    intervention.transaction_id
                )
                if existing is not None:
                    return existing
            raise RepositoryError(f"Supabase/PostgREST error: {exc}") from exc
        except Exception as exc:
            raise RepositoryError(f"Database call failed: {exc}") from exc
        return _deserialize(Intervention, res.data[0])

    async def update_intervention(self, intervention: Intervention) -> Intervention:
        # Match by id and rewrite the full column set (_serialize already drops
        # DB-generated columns). deleted_at IS NULL guards against touching a
        # soft-deleted legal record. Goes through _run, so a unique/network/
        # timeout failure is already translated to RepositoryError; no INSERT-
        # style idempotency handling applies (we update one existing row and
        # never change its transaction_id). No row matched -> a real bug.
        client = await get_client()
        res = await _run(
            client.table("interventions")
            .update(_serialize(intervention))
            .eq("id", str(intervention.id))
            .is_("deleted_at", "null")
        )
        if not res.data:
            raise RepositoryError(
                f"update_intervention matched no row (id={intervention.id})"
            )
        return _deserialize(Intervention, res.data[0])

    async def soft_delete_intervention(
        self, intervention_id: UUID, advisor_id: UUID
    ) -> Intervention | None:
        # A soft-delete IS an update: set deleted_at, never DELETE (hard rule 1).
        # The deleted_at IS NULL guard makes it idempotent (an already-deleted
        # row matches nothing -> None) and the advisor_id filter is the
        # authorization, like every intervention read. Server clock is fine
        # here: deleted_at is audit metadata, not a field-event date (rule 2
        # only binds treatment_date).
        client = await get_client()
        res = await _run(
            client.table("interventions")
            .update({"deleted_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", str(intervention_id))
            .eq("advisor_id", str(advisor_id))
            .is_("deleted_at", "null")
        )
        return _deserialize(Intervention, res.data[0]) if res.data else None

    async def list_interventions_in_period(
        self, holding_id: UUID, *, start: date, end: date
    ) -> list[Intervention]:
        client = await get_client()
        # created_at is a UTC timestamp; the period is civil dates. Bound with
        # [start 00:00, end+1day 00:00) so the whole `end` day is included. Minor
        # timezone fuzz at the day boundary is acceptable for a count (M7).
        res = await _run(
            client.table("interventions")
            .select("*")
            .eq("holding_id", str(holding_id))
            .gte("created_at", start.isoformat())
            .lt("created_at", (end + timedelta(days=1)).isoformat())
            .is_("deleted_at", "null")
            .order("created_at", desc=False)
        )
        return [_deserialize(Intervention, row) for row in res.data]

    async def list_validations(
        self, holding_id: UUID, campaign: str | None = None
    ) -> list[Validation]:
        client = await get_client()
        query = (
            client.table("validations")
            .select("*")
            .eq("holding_id", str(holding_id))
            .is_("deleted_at", "null")
        )
        if campaign is not None:
            query = query.eq("campaign", campaign)
        res = await _run(query)
        return [_deserialize(Validation, row) for row in res.data]

    async def save_validation(self, validation: Validation) -> Validation:
        client = await get_client()
        res = await _run(
            client.table("validations").insert(_serialize(validation))
        )
        return _deserialize(Validation, res.data[0])

    async def get_validation(
        self, validation_id: UUID, advisor_id: UUID
    ) -> Validation | None:
        client = await get_client()
        res = await _run(
            client.table("validations")
            .select("*")
            .eq("id", str(validation_id))
            .eq("advisor_id", str(advisor_id))  # scope = authorization
            .is_("deleted_at", "null")
            .limit(1)
        )
        return _deserialize(Validation, res.data[0]) if res.data else None

    async def list_holdings(self, advisor_id: UUID) -> list[Holding]:
        client = await get_client()
        res = await _run(
            client.table("holdings")
            .select("*")
            .eq("advisor_id", str(advisor_id))
            .is_("deleted_at", "null")
            .order("owner_name", desc=False)
        )
        return [_deserialize(Holding, row) for row in res.data]

    async def list_plots(self, holding_id: UUID) -> list[Plot]:
        client = await get_client()
        res = await _run(
            client.table("plots")
            .select("*")
            .eq("holding_id", str(holding_id))
            .is_("deleted_at", "null")
            .order("voice_alias", desc=False)
        )
        return [_deserialize(Plot, row) for row in res.data]

    # ── Onboarding writes (hackathon self-signup, TEMPORARY) ──
    async def _insert_one(self, table: str, obj, cls):
        """Insert one domain dataclass and return it re-read with DB defaults.

        A plain single-row insert (no idempotency race to resolve like
        save_intervention): OnboardingService already guards against a second
        run by checking for an existing advisor first. ``_run`` maps any
        PostgREST/network failure to a RepositoryError like every other write.
        """
        client = await get_client()
        res = await _run(client.table(table).insert(_serialize(obj)))
        return _deserialize(cls, res.data[0])

    async def save_advisor(self, advisor: Advisor) -> Advisor:
        return await self._insert_one("advisors", advisor, Advisor)

    async def save_holding(self, holding: Holding) -> Holding:
        return await self._insert_one("holdings", holding, Holding)

    async def save_plot(self, plot: Plot) -> Plot:
        return await self._insert_one("plots", plot, Plot)

    async def save_equipment(self, equipment: Equipment) -> Equipment:
        return await self._insert_one("equipment", equipment, Equipment)
