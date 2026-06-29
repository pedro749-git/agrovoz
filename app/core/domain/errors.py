"""Domain and infrastructure errors (spec §5).

Each domain error carries a stable ``code`` that the inbound API maps to
``{"error": "<CODE>", "mensaje": "<Spanish>"}`` (HTTP 422/404) and that the
``interventions.audit_state`` column reuses where applicable.
"""


class DomainError(Exception):
    """Base for business-rule violations. Subclasses set ``code``."""

    code = "DOMAIN_ERROR"


class DoseError(DomainError):
    """Applied/prescribed dose exceeds the product's legal maximum."""

    code = "DOSE_ERROR"


class ProductError(DomainError):
    """Product not authorized or expired."""

    code = "PRODUCT_ERROR"


class AreaError(DomainError):
    """Treated area exceeds the SIGPAC enclosure area."""

    code = "AREA_ERROR"


class MissingFieldError(DomainError):
    """LLM failed to extract a mandatory field from the audio."""

    code = "FIELD_ERROR"


class PlotNotFoundError(DomainError):
    """voice_alias does not exist for this advisor."""

    code = "PLOT_NOT_FOUND"


class EquipmentNotFoundError(DomainError):
    """equipment_alias does not exist for this advisor."""

    code = "EQUIPMENT_NOT_FOUND"


class InterventionNotFoundError(DomainError):
    """No intervention with that id belongs to this advisor (FLUJO B, M5)."""

    code = "INTERVENTION_NOT_FOUND"


class StateTransitionError(DomainError):
    """Illegal lifecycle transition (e.g. assess before execute)."""

    code = "STATE_TRANSITION_ERROR"


# ── Infrastructure ────────────────────────────────────────────────────────────


class InfrastructureError(Exception):
    """Base for failures in external services (not the advisor's fault).

    Named after the port, never the vendor: adapters translate provider
    errors (DashScope, AEMET, OSS...) into these at the boundary, so the
    core survives a provider swap untouched.
    """


class TranscriptionError(InfrastructureError):
    """The speech-to-text provider failed to transcribe the audio."""


class ExtractionError(InfrastructureError):
    """The LLM provider failed to extract fields from the transcription."""


class WeatherError(InfrastructureError):
    """The weather provider failed (leads to audit_state=WEATHER_PENDING)."""


class StorageError(InfrastructureError):
    """The object storage provider failed to upload/download a file."""


class RepositoryError(InfrastructureError):
    """The database/repository provider failed (network, PostgREST, constraint).

    A DB outage is infrastructure, not the advisor's fault, so the inbound maps
    it to 503 ("retry") rather than the catch-all 500 ("bug"). Idempotency races
    (a UNIQUE-violation retry) are resolved in the adapter, not raised as this.
    """
