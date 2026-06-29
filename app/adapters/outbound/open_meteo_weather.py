"""Open-Meteo adapter for the Weather port.

Open-Meteo is free and keyless (good for a TFG/hackathon): you ask for a lat/lon
and a date and get the conditions back. We use the *forecast* endpoint with an
explicit ``start_date``/``end_date`` — it also serves the recent past (~92 days),
which covers a deferred execution confirmed days or weeks later. Older than that
would need the archive endpoint; out of scope for the MVP.

We request HOURLY variables and read the 12:00 (local) sample as a representative
snapshot of the day, because the PWA does not capture the real application hour —
only the date. If that refines later (a real hour, or daily aggregates for drift
risk), it changes here and nowhere else.

AEMET stays pluggable behind the same port: swapping this for an AemetWeather
adapter is a one-line change in container.py.
"""

from datetime import date

import httpx

from app.core.domain.errors import WeatherError
from app.core.domain.models import WeatherData
from app.core.ports.weather import Weather

_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_HOURLY = "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m"
# Best-effort call: keep it short so a slow provider never delays the advisor's
# confirmation (a timeout just defers weather, it does not block — rule 8).
_TIMEOUT = 10.0
# Local hour read as representative of the application day (see module docstring).
_SAMPLE_HOUR = 12
# 8-point compass, starting at N and turning clockwise every 45°.
_COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _to_compass(degrees: float | None) -> str | None:
    """Wind direction in degrees -> 8-point compass label (None passes through)."""
    if degrees is None:
        return None
    return _COMPASS[round(degrees / 45) % 8]


def _sample_index(times: list[str]) -> int:
    """Index of the 12:00 reading in Open-Meteo's hourly ``time`` list (entries
    look like '2026-06-15T12:00'). Falls back to 0 if that hour is absent."""
    for i, t in enumerate(times):
        if t.endswith(f"T{_SAMPLE_HOUR:02d}:00"):
            return i
    return 0


def _at(values: list[float | None], i: int) -> float | None:
    """Safe lookup: Open-Meteo may return a None for an unavailable hour."""
    return values[i] if i < len(values) else None


class OpenMeteoWeather(Weather):
    async def conditions_at(self, *, lat: float, lon: float, day: date) -> WeatherData:
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": _HOURLY,
            "start_date": day.isoformat(),
            "end_date": day.isoformat(),
            "timezone": "Europe/Madrid",
            "wind_speed_unit": "kmh",
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(_FORECAST_URL, params=params, timeout=_TIMEOUT)
                resp.raise_for_status()
                hourly = resp.json()["hourly"]
            i = _sample_index(hourly["time"])
            return WeatherData(
                temperature_c=_at(hourly["temperature_2m"], i),
                relative_humidity_pct=_at(hourly["relative_humidity_2m"], i),
                wind_speed_kmh=_at(hourly["wind_speed_10m"], i),
                wind_direction=_to_compass(_at(hourly["wind_direction_10m"], i)),
            )
        except Exception as exc:
            # Single boundary (rule 8: never block the advisor): timeout, HTTP
            # status, malformed/missing JSON or an unexpected response shape ALL
            # become WeatherError — the only thing the service must handle
            # (-> audit_state=WEATHER_PENDING). Mirrors supabase_repo._run.
            raise WeatherError(f"Open-Meteo request failed: {exc}") from exc
