"""Port: render an intervention into its official PDF document."""

from abc import ABC, abstractmethod

from app.core.domain.models import (
    Advisor,
    Equipment,
    Holding,
    Intervention,
    Plot,
    Product,
    Validation,
)


class PdfGenerator(ABC):
    """Renders the legally-required PDF for an intervention.

    Synchronous on purpose: building a PDF is pure CPU work (no I/O), so it is
    not a coroutine. Async callers wrap it in ``asyncio.to_thread``. Uploading
    the result is a separate Storage port (that one is async/I/O).

    The document is a Spanish legal document (language rule: user-facing and
    legal text stays in Spanish, even though the code is English).
    """

    @abstractmethod
    def generate_prescription(
        self,
        *,
        intervention: Intervention,
        advisor: Advisor,
        holding: Holding,
        plot: Plot,
        product: Product,
        equipment: Equipment | None = None,
    ) -> bytes:
        """Return the prescription PDF (RD 1311/2012, Annex III) as bytes."""

    @abstractmethod
    def generate_validation(
        self,
        *,
        validation: Validation,
        advisor: Advisor,
        holding: Holding,
    ) -> bytes:
        """Return the advisor's signed campaign-validation PDF as bytes (M7).

        A conformity document over a holding's interventions in a period: the
        campaign, the period covered, the intervention count, the conformity
        verdict and remarks. Deterministic (built only from the persisted rows),
        so it can be regenerated if the OSS upload ever fails."""
