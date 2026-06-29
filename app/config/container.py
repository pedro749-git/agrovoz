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
from app.adapters.outbound.telegram import TelegramNotifier
from app.core.services.execution_service import ExecutionService
from app.core.services.registration_pipeline import RegistrationPipeline

transcriber = QwenTranscriber()
extractor = QwenExtractor()
repository = SupabaseRepository()
notifier = TelegramNotifier()
pdf_generator = ReportLabPdfGenerator()
storage = OssStorage()
weather = OpenMeteoWeather()

pipeline = RegistrationPipeline(
    transcriber, extractor, repository, pdf_generator, storage
)
execution_service = ExecutionService(repository, weather)
