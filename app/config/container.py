"""Composition root: build the adapters once and wire them into the services.

Plain module-level singletons — no DI framework (methodology: the simple thing
that works). Swapping an adapter (e.g. a different LLM) is a one-line change here
and nowhere else.
"""

from app.adapters.outbound.open_meteo_weather import OpenMeteoWeather
from app.adapters.outbound.oss_storage import OssStorage
from app.adapters.outbound.qwen import QwenExtractor, QwenTranscriber
from app.adapters.outbound.reportlab_pdf import ReportLabPdfGenerator
from app.adapters.outbound.supabase_repo import SupabaseRepository
from app.config.settings import settings
from app.core.services.assessment_service import AssessmentService
from app.core.services.campaign_validation_service import CampaignValidationService
from app.core.services.correction_service import CorrectionService
from app.core.services.execution_service import ExecutionService
from app.core.services.onboarding_service import OnboardingService
from app.core.services.registration_pipeline import RegistrationPipeline

transcriber = QwenTranscriber()
extractor = QwenExtractor()
repository = SupabaseRepository()
pdf_generator = ReportLabPdfGenerator()
storage = OssStorage()
weather = OpenMeteoWeather()

pipeline = RegistrationPipeline(
    transcriber, extractor, repository, pdf_generator, storage
)
execution_service = ExecutionService(
    repository, weather, settings.iteaf_validity_years
)
assessment_service = AssessmentService(repository)
# M8.2: correction (supersede) + soft-delete. Reuses the pipeline so a
# correction re-runs the same legal validation and PDF as a fresh FLUJO A.
correction_service = CorrectionService(repository, pipeline)
campaign_validation_service = CampaignValidationService(
    repository, pdf_generator, storage
)
# Hackathon self-signup only (TEMPORARY): seeds a demo advisor + sandbox for a
# fresh Supabase user. Delete alongside the flag and /api/bootstrap after the
# event.
onboarding_service = OnboardingService(repository)
