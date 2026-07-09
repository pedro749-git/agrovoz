# GIP Advisor — voice middleware for phytosanitary records

The advisor dictates a short voice note in the field (*"Finca de Pepe, Abamectina
1,5 litros por hectárea, araña roja, tractor"*) and the system produces the
legally valid phytosanitary record: transcription (Qwen-Audio) → field extraction
to JSON (Qwen Instruct) → legal validation → Supabase (PostgreSQL) → official PDF.

Legal context: Spanish RD 1311/2012 (Annex III) and EU Regulation 2023/564.
Electronic phytosanitary records become mandatory in Spain on 2027-01-01.

> Bachelor's thesis (TFG). The full specification lives in
> `docs/mvp_asesor_gip_v3.md` (in Spanish — the domain is Spanish-regulatory).

## Current status

Built in incremental milestones; each one works end-to-end before the next
begins.

- [x] **M1** — Spike: audio → JSON to the console (validate that Qwen
      understands a field advisor). Throwaway, archived at
      `docs/historico/spike_main.py`.
- [x] **M2** — **Verified end-to-end.** Telegram voice note → transcription +
      extraction with Qwen → legal validation → row persisted in Supabase.
      Hexagonal architecture (core + ports + adapters), fuzzy lookup of
      plot/product/equipment by the dictated alias.
- [x] **M3** — **Verified end-to-end.** Prescription PDF (ReportLab) + upload to
      Alibaba Cloud OSS, with a signed link (expires in 1h) downloaded from a phone.
- [x] **M4** — **Verified on a real phone.** Installable PWA (React + Vite +
      Tailwind): login via an email OTP code (or password), record button, audio
      upload to the same pipeline, today's records list and on-demand PDF download.
- [x] **M5** — State machine (OBSERVATION / PRESCRIBED → EXECUTED) + execution
      confirmation (FLUJO B: real dose/area/spray/operator, re-validated) +
      weather captured at the real date via Open-Meteo (with `WEATHER_PENDING` on
      failure) + ITEAF inspection expiry warning + PWA list → detail screen (with
      the actions on the detail).
- [x] **M6** — Effectiveness assessment (Good/Fair/Poor) + date + dictated reason
      + delivery-note number. EXECUTED → ASSESSED (`AssessmentService`), an
      assessment endpoint and a transcription-only endpoint; in the PWA, an
      assessment block on the detail with microphone dictation (transcribe →
      editable text) and a read-only view of the assessed record.
- [x] **M7** — Campaign validations. The advisor signs their conformity over a
      holding's records, mandatory twice per campaign (MID_CYCLE + FINAL), with a
      signed PDF. Backend (`CampaignValidationService`, holdings overview and
      validation endpoints) and PWA validation screen grouped by holding and
      campaign, with a 0/2 counter.

M1–M7 were the planned MVP. Since the hackathon deadline moved to 2026-07-20,
post-M7 work continues the same numbering as a **post-MVP hardening phase (M8+)**.

- [ ] **M8** (in progress) — Review-before-persist and correction of interventions.
      - [x] **M8.1** — FLUJO A split into `preview` (transcribe + extract, no save)
            and `commit` (persist the reviewed fields), so nothing from the LLM
            reaches the legal record unseen (hard rule 4). `preview` also resolves
            the dictated names against the catalog and canonicalizes them.
      - [ ] **M8.2** — Soft-delete of interventions + correction (supersede = new
            record + soft-delete of the old one, hard rules 1/7).
      - [x] **M8.3** — **Verified on a real phone.** Two-phase PWA record flow:
            record → review the extracted fields (prefilled with catalog-resolved
            names, a ✓/⚠️ marker per identity field, the plot's crop/SIGPAC) →
            confirm and save.

Also, since M7, an incremental polish pass (not a numbered milestone): a PWA
visual refresh (inline SVG icon set replacing emoji, shared app bar, refined
brand palette), a **history** screen with a date-range filter
(`/api/interventions` accepts `?from=&to=`), and voice dictation on the
campaign-validation remarks.

## Stack

**Backend**: Python 3.12 · FastAPI + Uvicorn · Pydantic V2 · Supabase
(PostgreSQL + Auth via email OTP code / password) · Qwen-Audio + Qwen Instruct
through DashScope · Alibaba Cloud OSS · ReportLab · weather via Open-Meteo.
Dependencies managed with `uv`.

**PWA (M4)**: React 19 + Vite + Tailwind + vite-plugin-pwa. Dependencies managed
with `npm`.

## Architecture (hexagonal, from M2 on)

```
app/
  core/        domain/ (models, schemas, states, errors, pure calculations)
               ports/  (ABCs: Transcriber, Extractor, Repository, Notifier,
                        Storage, PdfGenerator, Weather)
               services/ (registration_pipeline = FLUJO A · execution_service =
                          FLUJO B · assessment_service = FLUJO C ·
                          campaign_validation_service · validation_service)
  adapters/    inbound/  api.py (FastAPI: PWA REST API)
               outbound/ qwen.py · supabase_repo.py · oss_storage.py ·
                         reportlab_pdf.py · open_meteo_weather.py
  config/      settings.py · container.py (composition root) · .env
pwa/           React + Vite + Tailwind + vite-plugin-pwa (M4+ client)
```

The core depends only on ports (ABCs): the inbound adapter (the PWA REST API)
calls the pipeline (`POST /api/records`) without touching business logic.

## Local setup and run

**1. Install dependencies**
```bash
uv sync
```

**2. Configure the keys**
```bash
cp app/config/.env.example app/config/.env
# Fill in by hand: SUPABASE_URL/SERVICE_KEY, DASHSCOPE_API_KEY and OSS_*.
# The .env is never committed.
```

**3. Start the server** (port 8000, auto-reload)
```bash
uv run uvicorn app.adapters.inbound.api:app --host 127.0.0.1 --port 8000 --reload
```
Quick check: `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`.

The backend has no UI of its own — the client is the PWA (next section), which
calls this server over `/api/...`.

## PWA (M4)

The client the advisors use. It needs the backend running (previous section,
port 8000). From the repo root:

**1. Install dependencies** (first time only)
```bash
cd pwa
npm install
```

**2. Start the dev server** (Vite, port 5173)
```bash
npm run dev
```

**3. Expose it over HTTPS** (in another terminal) — the microphone and PWA
installation require a secure origin, so testing on a phone needs an HTTPS
tunnel, not `http://localhost`:
```bash
cloudflared tunnel --url http://localhost:5173
```
Open the `https://…trycloudflare.com` URL it prints on the phone, sign in with
the code emailed to you (or with a password), record a note and it shows up in
today's list.

## Safe shutdown

**Backend** — just stop Uvicorn (`Ctrl + C`).

**PWA** — just `Ctrl + C` in both terminals: the tunnel (`cloudflared`) first,
then Vite (`npm run dev`). Closing the tunnel destroys the `trycloudflare.com`
URL (they are ephemeral), so there is nothing to revoke.

## Tests

Few tests by methodology (one test per edge case, no exhaustive suite). The whole
suite at once:

```bash
uv run pytest
```

The suite covers:

| File | What it tests |
| --- | --- |
| `test_registration_pipeline.py` | FLUJO A end-to-end (with fake ports) |
| `test_execution_service.py` | FLUJO B: execution confirmation + weather + ITEAF warning |
| `test_assessment_service.py` | FLUJO C: effectiveness assessment (EXECUTED → ASSESSED) |
| `test_campaign_validation_service.py` | M7: campaign validation (period, conformity, remarks) |
| `test_validation_service.py` | legal validation (dose, area, authorized product) |
| `test_schemas.py` | `ExtractedFields` (sanitizing the LLM output) |
| `test_serialize_columns.py` | domain model ↔ DB columns (no drift) |
| `test_fuzzy_lookup.py` | fuzzy lookup of plot/product/equipment by alias |
| `test_states.py` | state-machine transitions |
| `test_auth.py` | Supabase JWT verification (`current_advisor_id`) |
| `test_api.py` | endpoints and error mapping to `{error, mensaje}` |

For a single file: `uv run pytest tests/test_registration_pipeline.py`.
