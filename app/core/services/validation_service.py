"""Legal validation (spec §4, hard rule 5) — runs BEFORE persisting.

Pure domain logic, no I/O: the pipeline resolves the rows (plot, product) and
hands them here. Each violation raises the typed domain error whose ``code``
the inbound maps to HTTP 422 and the ``interventions.audit_state`` column reuses.
"""

from app.core.domain.errors import AreaError, DoseError, ProductError
from app.core.domain.models import Plot, Product
from app.core.domain.schemas import ExtractedFields


def validate_legality(
    *,
    dose: float | None,
    dose_unit: str | None,
    treated_area_ha: float | None,
    plot: Plot,
    product: Product | None,
) -> None:
    """The legal checks over plain values. Raise on the first violation.

    Shared source of truth: FLUJO A validates the EXTRACTED values (via
    ``validate_registration``); FLUJO B (M5) re-validates the REAL applied dose
    and area at execution time. Both call this with the same plot/product.
    """
    if product is not None:
        # Product must be authorized in the MAPA vademecum.
        if not product.authorized:
            raise ProductError(
                f"El producto «{product.trade_name}» no está autorizado."
            )
        # Applied/prescribed dose must not exceed the legal maximum.
        if (
            dose is not None
            and product.max_allowed_dose is not None
            and dose > float(product.max_allowed_dose)
        ):
            raise DoseError(
                f"Dosis {dose} {dose_unit or ''} supera el máximo "
                f"legal de {product.max_allowed_dose} {product.dose_unit or ''} "
                f"para «{product.trade_name}»."
            )

    # Treated area can never exceed the SIGPAC enclosure area.
    if treated_area_ha is not None and treated_area_ha > float(plot.enclosure_area_ha):
        raise AreaError(
            f"Superficie tratada {treated_area_ha} ha supera la del "
            f"recinto SIGPAC ({plot.enclosure_area_ha} ha)."
        )


def validate_registration(
    fields: ExtractedFields, plot: Plot, product: Product | None
) -> None:
    """Raise on the first legal violation; return None if everything is legal.

    OBSERVATION records carry no product/dose, so only the area check (if any)
    applies to them. Thin wrapper over ``validate_legality`` with the extracted
    values.
    """
    validate_legality(
        dose=fields.dose,
        dose_unit=fields.dose_unit,
        treated_area_ha=fields.treated_area_ha,
        plot=plot,
        product=product,
    )
