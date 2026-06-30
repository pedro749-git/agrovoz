"""Pure domain calculations (no I/O, no ports).

Single-concept rules that several services share. Keeping them here — next to
states.py — instead of inline in a service means the registration pipeline and
the execution service (M5) compute them the same way, with one source of truth.
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


def iteaf_inspection_expired(
    treatment_date: datetime,
    inspection_date: date | None,
    validity_years: int,
) -> bool:
    """True when the equipment's ITEAF inspection is NOT valid on the treatment
    day — i.e. expired more than ``validity_years`` ago, or never recorded.

    The result feeds ``Intervention.iteaf_warning``: a non-blocking notice
    (never a block — the advisor is in the field), so the holding can renew the
    inspection. A missing inspection date counts as a warning on purpose: an
    unrecorded inspection cannot prove the machine is in-date.
    """
    if inspection_date is None:
        return True
    try:
        expiry = inspection_date.replace(year=inspection_date.year + validity_years)
    except ValueError:
        # Feb 29 inspected, non-leap expiry year -> fall back to Feb 28.
        expiry = inspection_date.replace(
            year=inspection_date.year + validity_years, day=28
        )
    return treatment_date.date() > expiry
