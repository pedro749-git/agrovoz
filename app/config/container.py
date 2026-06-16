"""Composition root: build the adapters once and wire them into the services.

Plain module-level singletons — no DI framework (methodology: the simple thing
that works). Swapping an adapter (e.g. a different LLM) is a one-line change here
and nowhere else.
"""

from app.adapters.outbound.qwen import QwenExtractor, QwenTranscriber
from app.adapters.outbound.supabase_repo import SupabaseRepository
from app.adapters.outbound.telegram import TelegramNotifier
from app.core.services.registration_pipeline import RegistrationPipeline

transcriber = QwenTranscriber()
extractor = QwenExtractor()
repository = SupabaseRepository()
notifier = TelegramNotifier()

pipeline = RegistrationPipeline(transcriber, extractor, repository)
