"""Legal validation (spec §4, hard rule 5) — runs BEFORE persisting.

Pure domain logic, no I/O: the pipeline resolves the rows (plot, product) and
hands them here. Each violation raises the typed domain error whose ``code``
the inbound maps to HTTP 422 and the ``interventions.audit_state`` column reuses.
"""

from app.core.domain.errors import AreaError, DoseError, ProductError
from app.core.domain.models import Plot, Product
from app.core.domain.schemas import ExtractedFields


def validate_registration(
    fields: ExtractedFields, plot: Plot, product: Product | None
) -> None:
    """Raise on the first legal violation; return None if everything is legal.

    OBSERVATION records carry no product/dose, so only the area check (if any)
    applies to them.
    """
    if product is not None:
        # Product must be authorized in the MAPA vademecum.
        if not product.authorized:
            raise ProductError(
                f"El producto «{product.trade_name}» no está autorizado."
            )
        # Applied/prescribed dose must not exceed the legal maximum.
        if (
            fields.dose is not None
            and product.max_allowed_dose is not None
            and fields.dose > float(product.max_allowed_dose)
        ):
            raise DoseError(
                f"Dosis {fields.dose} {fields.dose_unit or ''} supera el máximo "
                f"legal de {product.max_allowed_dose} {product.dose_unit or ''} "
                f"para «{product.trade_name}»."
            )

    # Treated area can never exceed the SIGPAC enclosure area.
    if (
        fields.treated_area_ha is not None
        and fields.treated_area_ha > float(plot.enclosure_area_ha)
    ):
        raise AreaError(
            f"Superficie tratada {fields.treated_area_ha} ha supera la del "
            f"recinto SIGPAC ({plot.enclosure_area_ha} ha)."
        )
