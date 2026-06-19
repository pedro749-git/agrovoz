"""Supabase adapter implementing the Repository port.

Uses the service_role key, which bypasses RLS — correct for M2, where the
inbound is the trusted backend (Telegram stand-in has no Supabase Auth JWT).
The RLS policies in the migration protect the future PWA path (M4+), where
each advisor authenticates with a magic link.

Every read filters ``deleted_at IS NULL`` (hard rule 1: soft-delete only).
"""

import dataclasses
from datetime import date, datetime
from enum import Enum
from typing import get_args, get_type_hints
from uuid import UUID

from supabase import AsyncClient, create_async_client

from app.adapters.outbound._fuzzy import best_match
from app.config.settings import settings
from app.core.domain.models import (
    Advisor,
    Equipment,
    Holding,
    Intervention,
    Plot,
    Product,
)
from app.core.domain.states import LifecycleState
from app.core.ports.repository import Repository

_client: AsyncClient | None = None


async def get_client() -> AsyncClient:
    """Create the async Supabase client once and reuse it (singleton)."""
    global _client
    if _client is None:
        _client = await create_async_client(
            settings.supabase_url,
            settings.supabase_service_key.get_secret_value(),
        )
    return _client


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
    """
    persisted = {
        f.name
        for f in dataclasses.fields(obj)
        if f.name not in _DB_GENERATED and f.metadata.get("persist", True)
    }
    return {
        k: _to_json(v)
        for k, v in dataclasses.asdict(obj).items()
        if k in persisted
    }


class SupabaseRepository(Repository):
    async def get_advisor(self, advisor_id: UUID) -> Advisor | None:
        client = await get_client()
        res = await (
            client.table("advisors")
            .select("*")
            .eq("id", str(advisor_id))
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        return _deserialize(Advisor, res.data[0]) if res.data else None

    async def get_advisor_by_auth_user_id(
        self, auth_user_id: UUID
    ) -> Advisor | None:
        client = await get_client()
        res = await (
            client.table("advisors")
            .select("*")
            .eq("auth_user_id", str(auth_user_id))
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        return _deserialize(Advisor, res.data[0]) if res.data else None

    async def list_interventions(
        self, advisor_id: UUID, *, state: LifecycleState | None = None
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
        res = await query.order("created_at", desc=True).limit(100).execute()
        return [_deserialize(Intervention, row) for row in res.data]

    async def get_holding(self, holding_id: UUID) -> Holding | None:
        client = await get_client()
        res = await (
            client.table("holdings")
            .select("*")
            .eq("id", str(holding_id))
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        return _deserialize(Holding, res.data[0]) if res.data else None

    async def get_intervention_by_transaction_id(
        self, transaction_id: UUID
    ) -> Intervention | None:
        client = await get_client()
        res = await (
            client.table("interventions")
            .select("*")
            .eq("transaction_id", str(transaction_id))
            .is_("deleted_at", "null")
            .limit(1)
            .execute()
        )
        return _deserialize(Intervention, res.data[0]) if res.data else None

    async def get_plot_by_alias(self, advisor_id: UUID, voice_alias: str) -> Plot | None:
        client = await get_client()
        # Fetch the advisor's plots (few) and fuzzy-match the dictated alias
        # against the real rows — the ASR mis-hears proper nouns.
        res = await (
            client.table("plots")
            .select("*, holdings!inner(advisor_id)")
            .eq("holdings.advisor_id", str(advisor_id))
            .is_("deleted_at", "null")
            .execute()
        )
        row = best_match(voice_alias, res.data, "voice_alias")
        return _deserialize(Plot, row) if row else None

    async def get_product_by_name(self, trade_name: str) -> Product | None:
        client = await get_client()
        # M2: fuzzy-match over the (small) seeded catalog. At vademecum scale
        # (thousands), replace this full fetch with a pg_trgm similarity query.
        # No authorized filter here: an unauthorized hit still resolves, so the
        # validation service can raise the precise "not authorized" error.
        res = await client.table("products").select("*").execute()
        row = best_match(trade_name, res.data, "trade_name")
        return _deserialize(Product, row) if row else None

    async def get_equipment_by_alias(
        self, advisor_id: UUID, equipment_alias: str
    ) -> Equipment | None:
        client = await get_client()
        res = await (
            client.table("equipment")
            .select("*, holdings!inner(advisor_id)")
            .eq("holdings.advisor_id", str(advisor_id))
            .is_("deleted_at", "null")
            .execute()
        )
        row = best_match(equipment_alias, res.data, "equipment_alias")
        return _deserialize(Equipment, row) if row else None

    async def save_intervention(self, intervention: Intervention) -> Intervention:
        client = await get_client()
        res = await (
            client.table("interventions")
            .insert(_serialize(intervention))
            .execute()
        )
        return _deserialize(Intervention, res.data[0])
