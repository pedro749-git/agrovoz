# Design decisions log

One line per decision (taken AND discarded): what · why · date.
This file becomes the thesis' design chapter.

## 2026-06-19 — Test audit + suite standardization

- Test style migrated from one monolithic main()+prints per file to one
  function per case (pytest-native) · granular pass/fail reporting and failures
  no longer hide the cases after them; standard idiom is more defensible for the
  TFG · 2026-06-19
- Adopt pytest.raises / parametrize / monkeypatch + a TestClient fixture · the
  idiomatic tools now that pytest is the committed runner · 2026-06-19
- No pytest-asyncio dependency · async bodies run via asyncio.run() inside sync
  test functions; keeps the dev deps lean · 2026-06-19
- pyproject [tool.pytest.ini_options] pythonpath=["."] · removes the per-file
  sys.path hack; tests run only via `uv run pytest` (dropped the __main__
  script-runners) · 2026-06-19
- New coverage: validation_service, states, schemas (trust boundary), auth (M4),
  api inbound (error→HTTP mapping). DELIBERATELY NOT covered: the thin SDK
  adapters (qwen/oss/reportlab/telegram, supabase_repo body) — testing them is
  mocking the SDK, low ROI; supabase_repo already has the serialize guard ·
  2026-06-19
- Audit found no behavioural bugs · confirmed dose/area limits are inclusive
  (rule is >, not >=), error→HTTP mapping (404/422/503/500/401) and the catch-all
  all behave as intended · 2026-06-19

## 2026-06-19 — M4 step 3: list endpoint + API safety net

- GET /api/interventions scoped to the authenticated advisor (same
  current_advisor_id dependency), optional ?state= filter (enum-validated by
  FastAPI → bad value is an automatic 422), newest first, limit 100 · spec §7 ·
  2026-06-19
- List uses a sync _record_fields projection (no presigned URL per row — N OSS
  calls would not scale); carries has_pdf, the detail view signs on demand. The
  create response = _record_fields + a single presigned pdf_url · 2026-06-19
- "del día" date filter deferred to Home wiring · "today" is timezone-dependent
  (Madrid vs UTC) and which timestamp to use is a UX call; decide it with the
  real screen, not blind · 2026-06-19
- App-level catch-all exception handler (Exception → 500 in {"error","mensaje"})
  added · the HTTP routes had no safety net (unlike the Telegram webhook), so a
  raw Supabase/PostgREST failure in the auth advisor-lookup OR the pipeline
  leaked as a bare 500. More specific handlers still win (dispatch by type) ·
  2026-06-19
- DISCARDED (for now) translating repository errors into InfrastructureError at
  the adapter boundary (the "correct" per errors.py) · touches every repo method;
  the catch-all covers it cheaply for M4. Revisit when the repo grows · 2026-06-19

## 2026-06-19 — M4 step 2: Supabase JWT auth (JWKS, ES256)

- Verify the access token against the asymmetric signing keys via the JWKS
  endpoint (derived from supabase_url), NOT the legacy HS256 shared secret ·
  CLAUDE.md mandate; asymmetric verification needs only public keys, so no new
  secret in .env · 2026-06-19
- Backend verifies the JWT itself + uses service_role for DB (bypasses RLS) ·
  the PWA talks to FastAPI, not to Supabase directly, so identity is enforced in
  the backend; the migration's RLS is a second layer, not this path · 2026-06-19
- advisor resolved by advisors.auth_user_id = token ``sub`` · a valid token whose
  user is not an advisor → 401 (authenticated ≠ authorized) · 2026-06-19
- Verification lives in its own inbound module app/adapters/inbound/auth.py (not
  api.py, unlike the error handlers) · ~50 lines, self-contained, reused by
  future routes — extraction earns its cost here · 2026-06-19
- AuthError → 401 via its own exception_handler, same {"error","mensaje"} shape ·
  auth is an HTTP-boundary concern, kept out of core domain errors · 2026-06-19
- HTTPBearer(auto_error=False) · a missing header becomes our AuthError 401, not
  FastAPI's default 403, so every auth failure shares one shape · 2026-06-19
- JWKS fetch + jwt.decode run via asyncio.to_thread · blocking I/O kept off the
  event loop; PyJWKClient caches keys, refetch only on unknown kid · 2026-06-19
- Library: PyJWT[crypto] (cryptography backs ES256) · 2026-06-19

## 2026-06-18 — M4 step 1: PWA inbound endpoint (POST /api/records)

- Second inbound route over the SAME pipeline · hexagonal: Telegram and the PWA
  are two inbound adapters on one core, no business-logic change (as api.py
  already anticipated) · 2026-06-18
- Synchronous (no background task, unlike Telegram) · the PWA UI waits for the
  outcome to show (saved record or 422 dose/area error); Telegram backgrounds
  only because it ACKs to avoid webhook-retry timeouts · 2026-06-18
- Error translation via app-level `exception_handler` (not try/except per route)
  · one policy shared by all HTTP routes; *_NOT_FOUND→404, other DomainError→422,
  InfrastructureError→503 as {"error","mensaje"} (spec §7) · 2026-06-18
- Handlers kept in api.py, NOT a separate error_handlers.py · only two + small,
  and error→HTTP translation is the inbound adapter's own job; extract via
  register_error_handlers(app) when it grows (>250 lines / more handlers) ·
  2026-06-18
- Auth deferred to M4 step 2 · reuse the default_advisor_id stand-in so the
  endpoint is curl-testable now; JWKS JWT verification lands next · 2026-06-18
- GPS left out of the request · pipeline.register doesn't take it and AEMET is
  M5; a silently-dropped gps field would mislead. Add it with AEMET · 2026-06-18
- Response is a focused JSON projection, not the raw Intervention · internal
  traceability fields (raw_transcription, prompt_version, storage keys) stay out
  of the API; best-effort presigned pdf_url like the Telegram summary · 2026-06-18

## 2026-06-18 — Review feedback: robust save + error catch-all

- `_serialize` filters to real columns explicitly (skips DB-generated +
  fields tagged `metadata={"persist": False}`) instead of dumping the whole
  dataclass · a model field that is not a column would otherwise blow up the
  INSERT with an opaque PostgREST error, hard to trace · 2026-06-18
- New `tests/test_serialize_columns.py` parses the migration and asserts the
  insert payload == real columns (minus generated) · detects model<->schema
  drift in both directions at test time, no DB/credentials needed · 2026-06-18
- Catch-all `except Exception` + `logger.exception` added to `_handle_update`
  (Telegram background task) · an unhandled error in a BackgroundTask dies
  silently and leaves the advisor stuck on "procesando…"; the log trace is
  how you see *why* it failed · 2026-06-18
- DISCARDED a global FastAPI `@app.exception_handler` for now · it only fires
  in the request→response cycle, but the Telegram work runs in a
  BackgroundTask after the ACK; the right home for it is the synchronous PWA
  HTTP path (M4), not built ahead of need · 2026-06-18
- DISCARDED translating `httpx` errors in `download_voice` to
  `InfrastructureError` · the catch-all already handles them; per-adapter
  translation buys nothing today (Qwen/OSS already translate at their
  boundary, Supabase/Telegram fall through to the catch-all) · 2026-06-18
- Telegram `transaction_id` derived as `uuid5(ns, update_id)` instead of a
  fresh `uuid4()` per webhook call · Telegram redelivers the same `update_id`
  on retry, so a per-call uuid4 defeated hard rule 3 (idempotency) → duplicate
  records of one audio. Deterministic key makes a redelivery hit the existing
  row. PWA (M4) sends its own `crypto.randomUUID()` · 2026-06-18
- Split `_handle_update` into router + `_process_message` · the catch-all
  only covered the inner `try`, so update parsing before it (a `KeyError` on
  `message["from"]`/`["date"]`, the early notifier sends) could still die
  silently in the BackgroundTask. Now chat_id extraction is the only thing
  outside the net (guarded: no sender → log + drop, nobody to reply to) and
  ALL processing sits under one error policy · 2026-06-18
- `_summary` PDF-link block widened to `except InfrastructureError` +
  `except Exception` · building the presigned link must NEVER turn an
  already-saved record into an error message to the advisor · 2026-06-18
- `_store_prescription_pdf` now catches `Exception`, not just `StorageError` ·
  a ReportLab render bug sat inside the try and ran BEFORE save_intervention,
  so it blocked the legal record — contradicting the stated best-effort
  intent. Now any render/upload failure logs + saves without a PDF key · 2026-06-18
- `TelegramNotifier.send_message` adds `raise_for_status` + `except
  httpx.HTTPError` -> log warning, never raise · notifications are
  best-effort: a failed send must not break the flow nor make a saved record
  look failed (it silently swallowed HTTP errors before) · 2026-06-18
- Adopted `pytest` as a dev dependency (`uv run pytest` runs all) · reverses
  the earlier "no pytest yet" note: it was written with a single test, now
  there are 3 and running them one by one is friction. Only the *runner*
  changes — still few tests, no exhaustive suite. Files keep their
  `if __name__` block so they also run standalone · 2026-06-18

## 2026-06-17 — M3 step 2: PDF upload to OSS (FLUJO A, PRESCRIPTION)

- New async `Storage` port + `OssStorage` adapter (oss2) · uploading is network
  I/O, so the port is async (mirror of PdfGenerator being sync CPU); the port
  takes/returns bytes and never knows it is a PDF · 2026-06-17
- `oss2` is a synchronous SDK → every network call wrapped in `asyncio.to_thread`
  to keep the event loop free; OSS errors translated to `StorageError` at the
  adapter boundary (provider-swap safe) · 2026-06-17
- OSS key = `prescriptions/{transaction_id}.pdf` · transaction_id is known
  BEFORE the INSERT, so the key is set on the entity and persisted in a single DB
  write (no separate update method); deterministic key → a retry overwrites the
  same object, consistent with idempotency · 2026-06-17
- PDF+upload is BEST-EFFORT in the pipeline: on `StorageError` (or missing
  holding) save the intervention with `prescription_pdf_key=None` · a storage
  failure must never block the legal record (same principle as rule 8/AEMET); the
  PDF is deterministic and regenerable from the row · 2026-06-17
- Only the PRESCRIPTION branch generates the PDF (per spec FLUJO A) · a direct
  EXECUTION's document is the CUE execution record (M5/M6), not a prescription · 2026-06-17
- Added `Repository.get_holding` · the PDF needs the holding (owner/NIF/REA) and
  the pipeline only had `plot.holding_id`; fetched lazily inside the PDF step so
  OBSERVATION/EXECUTION don't pay the extra query · 2026-06-17
- Private bucket: the advisor gets a presigned GET URL (1h expiry) appended to the
  Telegram confirmation, not a public object URL · legal documents; chose the
  link over `sendDocument` to avoid widening the Notifier port in M3 · 2026-06-17
- Pipeline now depends on the `PdfGenerator` + `Storage` ports (injected via the
  container) · keeps the core pure and the wiring a one-line composition-root
  change · 2026-06-17

## 2026-06-16 — M3 step 1: prescription PDF (ReportLab, no OSS yet)

- Built the PDF generation first (port + ReportLab adapter), writing to disk,
  before touching OSS · lets us validate the legal template fast without an
  Alibaba bucket; OSS upload is step 2 · 2026-06-16
- `PdfGenerator.generate_prescription` is SYNCHRONOUS, not async · building a PDF
  is pure CPU (no I/O); async callers wrap it in asyncio.to_thread. The Storage
  port (OSS) will be the async/I/O one · 2026-06-16
- `generate_prescription` takes the domain entities (intervention, advisor,
  holding, plot, product, equipment) directly, not a new DTO · simpler and
  matches what the pipeline already resolves; a DTO would be abstraction ahead
  of need · 2026-06-16
- ReportLab via platypus (SimpleDocTemplate + Tables) instead of low-level
  canvas · the document is a label/value form, tables handle layout/wrapping
  for free · 2026-06-16
- Timestamps rendered in Europe/Madrid via zoneinfo (hard rule 9); naive
  datetimes treated as UTC · 2026-06-16
- Sample generator lives in tests/ and writes sample_prescription.pdf (gitignored)
  for visual review · not a real assertion suite, just an eyeball artifact · 2026-06-16

## 2026-06-16 — M2: fuzzy name resolution (ASR mis-hears proper nouns)

- The ASR mis-transcribes proper nouns ("Abamectina"→"amavectina", "Finca de
  Pepe"→"Finca de PP"), so exact `ilike` lookups failed · resolve dictated names
  by fuzzy-matching against the catalog instead of exact match · 2026-06-16
- Chose fuzzy-match-against-the-catalog over feeding domain vocabulary to the
  ASR · the MAPA vademecum is thousands of products — too many for ASR context,
  and a huge context degrades transcription; fuzzy matching scales and only ever
  resolves to a REAL row (never invents a value, hard rule 4) · 2026-06-16
- Rejected fuzzy-matching over free text · matching only against catalog rows +
  a similarity threshold + an ambiguity guard (refuse when the top two are
  equally close) keeps it legally safe; below threshold → None → the service
  tells the advisor, it never guesses · 2026-06-16
- Doses/quantities are NEVER fuzzy-matched, only identity (plot/product/
  equipment) · dose is an exact legal value; `raw_transcription` keeps what was
  actually heard for audit alongside the resolved row · 2026-06-16
- M2 matches in Python (`difflib`, stdlib — no new dependency) over small row
  sets; logged that product matching must move to a pg_trgm similarity query
  (DB-side, GIN trigram index) once the real vademecum is loaded · 2026-06-16
- Fuzzy helpers live in a pure module `adapters/outbound/_fuzzy.py` (no settings
  import) · unit-testable without env/DB · 2026-06-16
- Deferred confirm-before-persist + manual field correction to M5/M4 · the
  confirmation flow needs conversational state (callback handlers, draft store)
  and "execution confirmation" is M5 scope; the fuzzy threshold + the bot's
  echo-back summary + correctable records (M5: correction = new intervention +
  soft-delete) are enough safety for M2 · 2026-06-16

## 2026-06-15 — M2: registration pipeline (FLUJO A) wired end-to-end

- FastAPI is THE inbound; the Telegram webhook is one thin route over the core
  pipeline, the future PWA (M4) will be a second route on the SAME pipeline ·
  Telegram is a stand-in client until the PWA exists; hexagonal lets us swap the
  transport without touching business logic · 2026-06-15
- The pipeline does NOT depend on the Notifier port (it raises/returns) ·
  how to answer is transport specific (Telegram message vs HTTP 422 JSON), so
  notification stays in the inbound adapter; keeps the core fully pure · 2026-06-15
- M2 Telegram stand-in compromises (revisit at M4): `advisor_id` from a single
  `DEFAULT_ADVISOR_ID` setting, `transaction_id` minted server-side (PWA will
  send crypto.randomUUID()), `device_timestamp` = Telegram message date ·
  Telegram carries no auth/UUID/device clock; documented debt, not a design · 2026-06-15
- `prompt_version` added to the Extractor port (read-only property) · the legal
  trace (interventions.prompt_version) must hold for any extractor, so it is part
  of the contract, not a Qwen detail · 2026-06-15
- Generic `_serialize`/`_deserialize` helpers in the Supabase adapter (coerce by
  dataclass type hints) instead of a hand-written mapper per entity · less code
  for a student to read and one place to fix coercion bugs · 2026-06-15
- Audio sent to Qwen as a base64 data URI instead of a temp file · avoids
  touching the filesystem on the server; the M1 temp-file path was spike-only · 2026-06-15
- supabase_repo uses the service_role key (bypasses RLS) · M2 backend is trusted
  and the Telegram stand-in has no Supabase Auth JWT; the migration's RLS still
  guards the PWA path · 2026-06-15
- Dropped `SUPABASE_JWT_SECRET` from config · no JWT to verify until the PWA
  authenticates (M4), and the legacy shared HS256 secret is deprecated by
  Supabase; verify via the asymmetric signing keys / JWKS endpoint when M4 needs
  it · 2026-06-16

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
