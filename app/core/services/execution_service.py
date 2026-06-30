"""FLUJO B — execution confirmation (M5).

A PRESCRIBED intervention -> EXECUTED with the REAL application data the advisor
confirms. Pure orchestration over the Repository port; the weather block and
audit_state are left untouched here — capturing Open-Meteo conditions is the
next M5 step.

Mirrors RegistrationPipeline (FLUJO A): a class with the ports injected, wired
in container.py. It RAISES typed domain errors and RETURNS the updated
intervention; the inbound adapter decides how to surface that.
"""

import logging
from datetime import datetime
from uuid import UUID

from app.core.domain.calculations import (
    earliest_harvest_date,
    iteaf_inspection_expired,
)
from app.core.domain.errors import (
    InterventionNotFoundError,
    PlotNotFoundError,
    WeatherError,
)
from app.core.domain.models import Intervention, Plot
from app.core.domain.states import LifecycleState, transition
from app.core.ports.repository import Repository
from app.core.ports.weather import Weather
from app.core.services.validation_service import validate_legality

logger = logging.getLogger(__name__)


class ExecutionService:
    """Confirms a prescription's execution (FLUJO B)."""

    def __init__(
        self, repository: Repository, weather: Weather, iteaf_validity_years: int
    ) -> None:
        self._repo = repository
        self._weather = weather
        # Years an ITEAF inspection stays valid (from settings; see rule below).
        self._iteaf_validity_years = iteaf_validity_years

    async def confirm(
        self,
        *,
        intervention_id: UUID,
        advisor_id: UUID,
        treatment_date: datetime,
        applied_dose: float | None = None,
        treated_area_ha: float | None = None,
        operator_name: str | None = None,
        operator_ropo: str | None = None,
        spray_volume_l_ha: float | None = None,
        delivery_note_number: str | None = None,
    ) -> Intervention:
        """Confirm the execution of a PRESCRIBED intervention with the REAL data.

        ``treatment_date`` is the REAL application date, sent by the client — the
        PWA prefills it with the device clock (editable, since the treatment may
        have been applied days before it is confirmed), never the server clock
        (hard rule 2: the server has only its own time, which sync would skew).
        Every other field is optional: None means "keep the prescribed value /
        the holding default".
        """
        # Load scoped to the advisor: requesting someone else's record is an
        # indistinguishable 404 (you cannot probe what is not yours).
        intervention = await self._repo.get_intervention(intervention_id, advisor_id)
        if intervention is None:
            raise InterventionNotFoundError("No encuentro ese registro.")

        # State gate: only PRESCRIBED -> EXECUTED. Anything else (already
        # executed, observation, assessed) raises StateTransitionError -> 422.
        # A double confirm is therefore rejected here, no idempotency key needed.
        transition(intervention, LifecycleState.EXECUTED)

        # Resolve the real figures, falling back to the prescription / holding.
        holding = await self._repo.get_holding(intervention.holding_id)
        applied_dose = (
            applied_dose if applied_dose is not None else intervention.prescribed_dose
        )
        operator_name = operator_name or (
            holding.default_operator_name if holding else None
        )
        operator_ropo = operator_ropo or (
            holding.default_operator_ropo if holding else None
        )

        # Re-validate legality with the REAL dose/area (hard rule 5): they can
        # differ from what was prescribed. Needs the plot (area cap) and the
        # product (dose cap).
        plot = await self._repo.get_plot(intervention.plot_id)
        if plot is None:
            raise PlotNotFoundError("No encuentro la parcela de este registro.")
        product = None
        if intervention.product_registration_number is not None:
            product = await self._repo.get_product_by_registration_number(
                intervention.product_registration_number
            )
        validate_legality(
            dose=applied_dose,
            dose_unit=product.dose_unit if product else None,
            treated_area_ha=treated_area_ha,
            plot=plot,
            product=product,
        )

        # Apply the execution block onto the entity, then persist.
        intervention.treatment_date = treatment_date
        intervention.applied_dose = applied_dose
        intervention.dose_unit = (
            product.dose_unit if product else intervention.dose_unit
        )
        intervention.treated_area_ha = treated_area_ha
        intervention.spray_volume_l_ha = spray_volume_l_ha
        intervention.operator_name = operator_name
        intervention.operator_ropo = operator_ropo
        intervention.delivery_note_number = delivery_note_number
        intervention.earliest_harvest_date = earliest_harvest_date(
            treatment_date,
            product.pre_harvest_interval_days if product else None,
        )

        # ITEAF warning: is the machine's inspection still valid on the REAL
        # treatment day? Only checkable when an equipment is linked (an
        # OBSERVATION has none). A non-blocking notice (rule 8 spirit).
        if intervention.equipment_id is not None:
            equipment = await self._repo.get_equipment(intervention.equipment_id)
            intervention.iteaf_warning = iteaf_inspection_expired(
                treatment_date,
                equipment.iteaf_inspection_date if equipment else None,
                self._iteaf_validity_years,
            )

        # Weather at the plot on the REAL application day (rule 8). Best-effort:
        # sets audit_state to VALID or WEATHER_PENDING, never raises, never blocks.
        await self._capture_weather(intervention, plot)

        return await self._repo.update_intervention(intervention)

    async def _capture_weather(self, intervention: Intervention, plot: Plot) -> None:
        """Capture the plot's conditions on the real application day (rule 8).

        Best-effort: weather is a good practice, not a legal blocker. If the plot
        has no coordinates or the provider fails, mark WEATHER_PENDING and leave
        the weather fields empty — the record still saves and the gap is auditable
        (a later backfill can fill it). Uses the plot centroid; the PWA does not
        send device GPS yet, so gps_lat/gps_lon stay None.
        """
        if plot.lat is None or plot.lon is None:
            intervention.audit_state = "WEATHER_PENDING"
            logger.warning("Plot %s has no coordinates; weather deferred", plot.id)
            return
        try:
            conditions = await self._weather.conditions_at(
                lat=plot.lat, lon=plot.lon, day=intervention.treatment_date.date()
            )
        except WeatherError:
            intervention.audit_state = "WEATHER_PENDING"
            logger.warning(
                "Weather capture failed for plot %s; deferred", plot.id, exc_info=True
            )
            return
        intervention.temperature_c = conditions.temperature_c
        intervention.relative_humidity_pct = conditions.relative_humidity_pct
        intervention.wind_speed_kmh = conditions.wind_speed_kmh
        intervention.wind_direction = conditions.wind_direction
        intervention.audit_state = "VALID"
