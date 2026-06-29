"""Port: weather conditions at a plot on the real application day.

Captured when an EXECUTION is confirmed (hard rule 8), never at prescription —
the conditions that matter are those when the treatment was actually applied,
which may be days before the advisor confirms it. Hence ``day`` is a parameter,
not "now": the adapter must serve historical data for a deferred execution.

Contract (so the caller only has to handle one thing): an implementation either
returns a ``WeatherData`` or raises ``WeatherError`` — every provider failure
(timeout, bad status, malformed response) is translated to ``WeatherError`` at
the adapter boundary, so the core survives a provider swap (today Open-Meteo;
AEMET stays pluggable here).
"""

from abc import ABC, abstractmethod
from datetime import date

from app.core.domain.models import WeatherData


class Weather(ABC):
    @abstractmethod
    async def conditions_at(self, *, lat: float, lon: float, day: date) -> WeatherData:
        """Conditions at (``lat``, ``lon``) on ``day``. Raises ``WeatherError``.

        The caller treats any failure as non-blocking (audit_state=WEATHER_PENDING):
        weather is a good practice, not a legal blocker on the record.
        """
