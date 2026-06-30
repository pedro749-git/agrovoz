"""Guard against the silent save trap (M2 review feedback).

``_serialize`` used to dump the whole dataclass; the day a model field stopped
mapping to a real column, the INSERT blew up with an opaque PostgREST error.
This parses each table's columns straight from the migration and asserts the
serialized insert payload contains EXACTLY the columns the DB does not generate
itself — so model<->schema drift fails HERE, loudly. No DB or credentials needed.
Run: uv run pytest tests/test_serialize_columns.py
"""

import re
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.adapters.outbound.supabase_repo import _DB_GENERATED, _serialize
from app.core.domain.models import (
    Advisor,
    Equipment,
    Holding,
    Intervention,
    Plot,
    Product,
)
from app.core.domain.states import LifecycleState

ROOT = Path(__file__).resolve().parents[1]
# Concatenate ALL migrations (sorted): the schema lives in the first, later
# ones add constraints/indexes — every CREATE TABLE must be in scope here.
_SQL = "\n".join(
    m.read_text() for m in sorted((ROOT / "supabase" / "migrations").glob("*.sql"))
)

# Table-level constraints, not columns: skip lines that start with these.
_NOT_A_COLUMN = ("CHECK", "UNIQUE", "PRIMARY", "FOREIGN", "CONSTRAINT")


def _columns(table: str) -> set[str]:
    """Column names declared in the ``CREATE TABLE <table> ( ... );`` block."""
    body = re.search(rf"CREATE TABLE {table} \((.*?)\n\);", _SQL, re.S).group(1)
    cols = set()
    for line in body.splitlines():
        line = line.strip()
        # A column line is "<name> <TYPE> ...". Comment lines start with --,
        # continuation lines (CHECK value lists) start with '(' -> no match.
        m = re.match(r"([a-z_]+)\s+\w", line)
        if m and not line.upper().startswith(_NOT_A_COLUMN):
            cols.add(m.group(1))
    return cols


NOW = datetime(2026, 6, 18, tzinfo=timezone.utc)
UID = uuid4()

# One representative instance per persisted entity, with every mandatory field
# set (values are irrelevant — we only compare the SET of payload keys).
CASES = [
    ("advisors", Advisor(full_name="X", dni="1", ropo_number="R")),
    ("holdings", Holding(advisor_id=UID, owner_name="X", owner_nif="1",
                         rea_regepa_number="R")),
    ("plots", Plot(holding_id=UID, voice_alias="Finca", crop="Limonero",
                   enclosure_area_ha=5.0, sigpac_province="30",
                   sigpac_municipality="001", sigpac_polygon="1",
                   sigpac_parcel="1", sigpac_enclosure="1")),
    ("products", Product(registration_number="ES-1", trade_name="X",
                         active_substance="abamectina")),
    ("equipment", Equipment(holding_id=UID, equipment_alias="tractor")),
    ("interventions", Intervention(transaction_id=UID,
                                   lifecycle_state=LifecycleState.PRESCRIBED,
                                   advisor_id=UID, holding_id=UID, plot_id=UID,
                                   prescription_date=NOW,
                                   earliest_harvest_date=date(2026, 7, 1))),
]


@pytest.mark.parametrize("table,obj", CASES, ids=[c[0] for c in CASES])
def test_serialize_matches_schema(table, obj):
    payload = set(_serialize(obj).keys())
    expected = _columns(table) - set(_DB_GENERATED)
    assert payload == expected, (
        f"{table}: serialize <-> schema drift.\n"
        f"  in payload but not a column: {sorted(payload - expected)}\n"
        f"  column but missing from payload: {sorted(expected - payload)}")
