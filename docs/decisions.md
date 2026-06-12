# Design decisions log

One line per decision (taken AND discarded): what · why · date.
This file becomes the thesis' design chapter.

## 2026-06-12 — M1 → M2: hexagonal skeleton

- Created the M2 hexagonal skeleton (`core/{domain,ports,services}`,
  `adapters/{inbound,outbound}`, `config/`, `prompts/`, `spike/`); only folders +
  `__init__.py`, no speculative modules · honors "create folders from M2, implement
  ports/adapters on demand" · 2026-06-12
- Renamed `app/config.py` → `config/settings.py` · matches the documented layout
  and avoids confusing "config the module" with "config the package" · 2026-06-12
- `app/db.py` → `adapters/outbound/supabase_repo.py` · it is the DB outbound adapter · 2026-06-12
- `app/telegram.py` → `adapters/outbound/telegram.py` · classified as outbound (it is
  a Telegram API client: send messages, download voice files) · 2026-06-12
- `app/qwen.py` kept as a single `adapters/outbound/qwen.py` instead of splitting into
  `qwen_audio.py` + `qwen_instruct.py` (per layout) · they share the DashScope client
  setup and the split adds no value until the M2 transcriber/extractor ports exist —
  defer to M2 · 2026-06-12
- `app/main.py` → `spike/main.py` · current FastAPI + Telegram-webhook glue is M1
  throwaway orchestration; M2 will introduce the real `adapters/inbound/api.py` · 2026-06-12
- `Settings.env_file` now points at `config/.env` (was `.env`) · the env file lives next
  to `settings.py`; resolved relative to the project root (CWD) · 2026-06-12
- `.gitignore`: un-ignored `.env.example` (the `.env.*` rule was also hiding the
  template) so the committed example stays tracked · 2026-06-12
- Wrapped the code packages under a single top-level `app/` package
  (`app/core`, `app/adapters`, `app/config`); `spike/`, `prompts/`, `docs/` stay at
  the root · keeps generic names (`config`, `core`) out of the top-level import
  namespace and avoids clashes; diverges from the original flat spec layout (updated
  in CLAUDE.md) · imports become `app.<...>`; `env_file` → `app/config/.env` · 2026-06-12
- Kept empty `__init__.py` in every package folder · they declare real (non-namespace)
  packages so imports, pytest and mypy behave predictably · 2026-06-12

## 2026-06-12 — M2: domain layer (core/domain)

- Implemented the four domain modules from spec §5 (`errors.py`, `states.py`,
  `schemas.py`, `models.py`) · they are M2's foundation: everything else
  (ports, services, repo) depends on them · 2026-06-12
- `LifecycleState` as `StrEnum` instead of the spec's plain strings ·
  `LifecycleState.PRESCRIBED == 'PRESCRIBED'` keeps DB writes identical while
  preventing typos and giving IDE autocompletion; spec is a map, not a
  contract · 2026-06-12
- Added `DomainError`/`InfrastructureError` base classes with a `code` class
  attribute per domain error · M2's `api.py` needs ONE exception handler
  mapping `code` → `{"error": ..., "mensaje": ...}` instead of seven; codes
  reuse the `audit_state` vocabulary where it exists · 2026-06-12
- DB `DECIMAL` columns typed as `float` in dataclasses (not `Decimal`) · the
  Supabase JSON API returns floats anyway and the legal comparisons
  (dose ≤ max, area ≤ enclosure) don't need exact decimal arithmetic at this
  scale; matches `ExtractedFields` (spec uses `float`) · 2026-06-12
- Dataclasses mirror the FULL migration schema (including M5+ blocks like
  weather/effectiveness) even though M2 only persists the basics · the
  migration already created those columns, so this mirrors existing DB, it is
  not speculative; `id`/`created_at`/`updated_at` default to None (DB
  generates them) · 2026-06-12
- `Optional[X]` written as `X | None` throughout · consistency with the
  existing codebase (qwen.py) over the spec's `Optional[...]` style;
  functionally identical in Pydantic V2 · 2026-06-12
- No tests for the domain yet · CLAUDE.md scopes tests to prompt edge cases;
  the state machine was smoke-tested manually (all legal + illegal
  transitions) · 2026-06-12
- Renamed infrastructure errors from vendor names (`QwenError`, `AemetError`,
  `OssError`) to port names (`TranscriptionError`, `ExtractionError`,
  `WeatherError`, `StorageError`) · the core catches errors through the ports,
  so a provider swap (Qwen→Whisper, AEMET→other) must not touch the domain;
  adapters translate vendor errors at the boundary. Four errors instead of
  three because Qwen spans two ports (transcriber + extractor) · 2026-06-12

## 2026-06-12 — M2: ports (core/ports)

- Created the four ports M2's audio flow needs as async ABCs: `Transcriber`
  (bytes→text), `Extractor` (text→ExtractedFields), `Repository` (Supabase
  lookups + insert), `Notifier` (message back to the advisor) · "ABCs added
  on demand": storage/weather/pdf_generator wait for M3/M5 · 2026-06-12
- New port `notifier.py`, not in the original spec layout (added to CLAUDE.md
  and spec) · the pipeline runs as a background task (the webhook ACKs
  immediately), so the core must push results/errors to the advisor; named
  by function, not "telegram" — in M4+ the channel may become PWA push ·
  2026-06-12
- Downloading the Telegram voice file is NOT a port · fetching the audio is
  the inbound adapter's job; the core receives bytes (it never asks
  "download file_id X") · 2026-06-12
- Repository lookups return `None` instead of raising · which domain error a
  miss becomes (PlotNotFoundError vs ProductError...) is a business decision
  that belongs to the service, not to the persistence adapter · 2026-06-12
- ExtractedFields validation declared part of the Extractor port's contract ·
  hard rule 4 (LLM output is untrusted) must hold for ANY future extractor
  implementation, not just Qwen's · 2026-06-12
- One `Repository` ABC (not one per entity) with only FLUJO A's six methods ·
  a single port matches the spec layout and the single Supabase adapter;
  splitting per entity is abstraction ahead of need · 2026-06-12
