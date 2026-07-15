"""Legal validation (spec §4, hard rule 5) — runs BEFORE persisting.

Pure domain logic, no I/O: the pipeline resolves the rows (plot, product) and
hands them here. Each violation raises the typed domain error whose ``code``
the inbound maps to HTTP 422 and the ``interventions.audit_state`` column reuses.
"""

from app.core.domain.errors import AreaError, DoseError, ProductError
from app.core.domain.models import Plot, Product
from app.core.domain.schemas import ExtractedFields

# --- Dose-unit normalization --------------------------------------------------
# The max-dose comparison is only meaningful in the SAME unit: 0.5 hl/ha IS
# 50 L/ha, so comparing raw numbers would wave an illegal dose through. Each
# recognized numerator maps to (dimension, factor to the base unit — L or kg).
# Physical constants, not configuration: no DB column (no speculative fields).
# The extraction prompt (v2) pushes Qwen towards the compact spellings, but the
# LLM is untrusted (hard rule 4) and the advisor can edit the unit by hand, so
# dictation synonyms are accepted here too.
_NUMERATORS = {
    "l": ("volume", 1.0),
    "lt": ("volume", 1.0),
    "litro": ("volume", 1.0),
    "litros": ("volume", 1.0),
    "hl": ("volume", 100.0),
    "hectolitro": ("volume", 100.0),
    "hectolitros": ("volume", 100.0),
    "cl": ("volume", 0.01),
    "ml": ("volume", 0.001),
    "mililitro": ("volume", 0.001),
    "mililitros": ("volume", 0.001),
    "cc": ("volume", 0.001),
    "kg": ("mass", 1.0),
    "kilo": ("mass", 1.0),
    "kilos": ("mass", 1.0),
    "kilogramo": ("mass", 1.0),
    "kilogramos": ("mass", 1.0),
    "g": ("mass", 0.001),
    "gr": ("mass", 0.001),
    "gramo": ("mass", 0.001),
    "gramos": ("mass", 0.001),
}

# Denominators are NOT convertible between each other: "/ha" doses a surface,
# "/hl" doses the spray mix (a concentration). Comparing across them would need
# the actual spray volume, which the record may not carry -> incomparable.
_DENOMINATORS = {
    "ha": "ha",
    "hectarea": "ha",
    "hectareas": "ha",
    "hl": "hl",
    "hectolitro": "hl",
    "hectolitros": "hl",
}

_ACCENTS = str.maketrans("áéíóúü", "aeiouu")


def _parse_dose_unit(raw: str) -> tuple[str, float, str] | None:
    """``"hl/ha"`` -> ``("volume", 100.0, "ha")``; None when not recognized."""
    unit = raw.strip().lower().translate(_ACCENTS).replace(" ", "").replace(".", "")
    unit = unit.replace("por", "/")  # "litros por hectárea" -> "litros/hectarea"
    numerator, sep, denominator = unit.partition("/")
    if not sep or numerator not in _NUMERATORS or denominator not in _DENOMINATORS:
        return None
    dimension, factor = _NUMERATORS[numerator]
    return dimension, factor, _DENOMINATORS[denominator]


def _check_dose(dose: float, dose_unit: str | None, product: Product) -> None:
    """Raise DoseError unless the dose is provably within the legal maximum.

    The dictated dose is converted into the catalog's unit before comparing.
    When the units cannot be reasoned about (unknown spelling, or a /hl
    concentration against a /ha maximum) the app cannot certify legality
    (hard rule 5), so it refuses to persist rather than guess (hard rule 4).
    """
    dictated = _parse_dose_unit(dose_unit) if dose_unit else None
    catalog = _parse_dose_unit(product.dose_unit) if product.dose_unit else None

    if dose_unit and catalog is not None and dictated is None:
        raise DoseError(
            f"Unidad de dosis «{dose_unit}» no reconocida: indica la dosis "
            f"en {product.dose_unit} para «{product.trade_name}»."
        )

    checked = dose
    if dictated is not None and catalog is not None:
        if dictated[0] != catalog[0] or dictated[2] != catalog[2]:
            raise DoseError(
                f"No se puede comprobar la dosis: la unidad dictada "
                f"«{dose_unit}» no es comparable con la del catálogo "
                f"({product.dose_unit}). Indica la dosis en "
                f"{product.dose_unit} para «{product.trade_name}»."
            )
        checked = dose * dictated[1] / catalog[1]

    # No unit on either side: numeric comparison, the best available check.
    if checked > float(product.max_allowed_dose):
        converted = f" (= {checked:g} {product.dose_unit})" if checked != dose else ""
        raise DoseError(
            f"Dosis {dose} {dose_unit or ''}{converted} supera el máximo "
            f"legal de {product.max_allowed_dose} {product.dose_unit or ''} "
            f"para «{product.trade_name}»."
        )


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
        # Applied/prescribed dose must not exceed the legal maximum — compared
        # in the catalog's unit, never as raw numbers (0.5 hl/ha IS 50 L/ha).
        if dose is not None and product.max_allowed_dose is not None:
            _check_dose(dose, dose_unit, product)

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
