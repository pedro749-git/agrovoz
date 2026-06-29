"""Pure domain calculations (no I/O, no ports).

Single-concept rules that several services share. Keeping them here — next to
states.py — instead of inline in a service means the registration pipeline and
the execution service (M5) compute them the same way, with one source of truth.

(M5 will add the ITEAF-expiry check here once the inspection validity period is
decided — not added speculatively now.)
"""

from datetime import date, datetime, timedelta


def earliest_harvest_date(
    treatment_date: datetime, phi_days: int | None
) -> date | None:
    """Earliest legal harvest = treatment date + the product's pre-harvest
    interval (PHI). Returns None when the product has no PHI on record."""
    if phi_days is None:
        return None
    return treatment_date.date() + timedelta(days=phi_days)
