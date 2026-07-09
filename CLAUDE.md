# CLAUDE.md — GIP Advisor (TFG / internship / Alibaba hackathon)

## What this project is

Voice middleware for GIP advisors (Gestión Integrada de Plagas — Integrated
Pest Management) in Spain. The advisor dictates a short audio in the field
("Finca de Pepe, Abamectina 1.5 litros por hectárea, araña roja, tractor")
and the system produces the legally valid phytosanitary record: transcription
(Qwen-Audio) → field extraction to JSON (Qwen Instruct) → legal validation →
PostgreSQL → official PDF.

Legal context: Spanish RD 1311/2012 (Annex III) and EU Regulation 2023/564.
Electronic phytosanitary records become mandatory in Spain on 2027-01-01.

**Full specification lives in `docs/mvp_asesor_gip_v3.md` (in Spanish — the
domain is Spanish-regulatory). It is a map, not a contract: consult it when
needed, never implement it wholesale.**

## Methodology — READ BEFORE PROPOSING ANYTHING

Solo project (3rd-year CS student) built in incremental milestones. Golden
rule: **each milestone must work end-to-end before starting the next.**

- [x] M1 — SPIKE (throwaway, single file, NO architecture): audio in →
      extracted JSON printed to console. Goal: validate that Qwen understands a
      Spanish field advisor. 2-3 days max. Archived at
      `docs/historico/spike_main.py` (no longer runnable against current code).
- [x] M2 — Real repo starts HERE with the hexagonal skeleton (see Layout):
      JSON persisted to Supabase (all tables)
- [x] M3 — Prescription PDF (ReportLab) + upload to OSS (verified end-to-end:
      real upload + presigned URL downloaded from a phone)
- [x] M4 — Minimal PWA: record button + today's list (auth + upload + today's
      list + on-demand PDF download verified on a real phone)
- [x] M5 — Full state machine (OBSERVATION/PRESCRIBED→EXECUTED) + execution
      confirmation (FLUJO B: real dose/area/spray/operator, re-validated) +
      weather at execution via Open-Meteo (WEATHER_PENDING fallback) + ITEAF
      expiry warning + PWA list→detail screen with actions on the detail
- [x] M6 — Effectiveness assessment + delivery-note number
- [x] M7 — Campaign validations (signed PDF)

M1–M7 = the planned MVP. The hackathon deadline moved to 2026-07-20, so post-M7
continues the same numbering as a post-MVP hardening phase (M8+).

- [~] M8 — Review-before-persist + correction of interventions.
      - [x] M8.1 — FLUJO A split into preview (transcribe+extract, no save) +
            commit (persist reviewed fields); preview resolves + canonicalizes
            dictated names against the catalog (hard rule 4)
      - [ ] M8.2 — Soft-delete + correction (supersede = new record + soft-delete
            of the old one, hard rules 1/7)
      - [x] M8.3 — Two-phase PWA record flow (record → review → confirm), with
            per-field ✓/⚠️ resolution markers + plot crop/SIGPAC (verified on a phone)

**Update this checklist when a milestone is completed.** If the user asks for
something from a future milestone, point it out and ask before implementing.

Do NOT do (decided and justified in the spec — do not insist):
- NO abstractions ahead of need: create folders from M2, but only implement
  the ports/adapters the current milestone actually uses.
- NO exhaustive test suite yet; DO keep one test per prompt edge case (M1+).
- NO RLS/RBAC, NO Celery, NO formal migrations, NO Docker until there is
  more than one real user.
- NO speculative DB fields: every column must map to the official-fields
  checklist (spec §4) or a pipeline need.

## Repository layout (from M2 onward)

All code lives under a single top-level `app/` package (keeps generic names like
`config`/`core` out of the global import namespace). `prompts/`, `pwa/`
and `docs/` stay at the repo root.

```
app/
  core/
    domain/      models.py · schemas.py (Pydantic V2) · states.py · errors.py
    ports/       transcriber.py · extractor.py · repository.py
                 storage.py · weather.py · pdf_generator.py  (ABCs, added on demand)
    services/    registration_pipeline.py · execution_service.py
                 validation_service.py
  adapters/
    inbound/     api.py (FastAPI)
    outbound/    qwen.py (audio+instruct; split on demand) · supabase_repo.py
                 oss_storage.py · aemet_weather.py · reportlab_pdf.py
  config/        settings.py (pydantic-settings) · container.py · .env(.example)
pwa/             (M4+) React + Vite + Tailwind + vite-plugin-pwa
prompts/         extraction_v1.md  (few-shot examples; version bump on change)
docs/            mvp_asesor_gip_v3.md · decisions.md · historico/ (M1 spike)
```

## Language convention

- **All code identifiers, comments, commits and docs strings: English.**
- **Spanish regulatory acronyms are proper nouns — never translate:** ROPO,
  ROMA, SIGPAC, REA/REGEPA, ITEAF, GIP, CUE, SIEX, AEMET. Use them inside
  English identifiers: `ropo_number`, `sigpac_province`, `iteaf_inspection_date`.
- **User-facing text stays in Spanish:** UI strings, API error `mensaje`
  fields, PDFs (they are Spanish legal documents), demo audios.
- Canonical term mapping (spec is in Spanish):
  tecnicos→`advisors` · explotaciones→`holdings` · parcelas→`plots` ·
  recinto→`enclosure` · productos_mapa→`products` · maquinaria→`equipment` ·
  actuaciones→`interventions` · validaciones→`validations` ·
  aplicador→`operator` · dosis→`dose` · plaga_objetivo→`target_pest` ·
  plazo de seguridad→`pre_harvest_interval_days` (PHI) ·
  fecha_minima_cosecha→`earliest_harvest_date` ·
  estados: `OBSERVATION` / `PRESCRIBED` / `EXECUTED` / `ASSESSED`.

## Stack

- Python 3.12 + FastAPI + Uvicorn. Pydantic V2 (optionals MUST have `= None`).
- Supabase (PostgreSQL + Auth by email OTP code / password — magic link dropped
  for iPhone PWA compat; verify JWT via asymmetric signing keys / JWKS endpoint
  from M4 — not the legacy shared HS256 secret).
- Qwen-Audio (speech→text) + Qwen Instruct (text→JSON) via DashScope.
- Alibaba Cloud OSS (audio + PDFs), ReportLab (PDFs), AEMET OpenData (weather).
- Deployment target: Alibaba Cloud ECS (hackathon requirement).

```bash
uvicorn app.adapters.inbound.api:app --reload  # M2+ dev server (run from repo root)
uv sync                                       # install deps from pyproject/uv.lock
cp app/config/.env.example app/config/.env    # fill keys manually, never commit .env
```

## Hard domain rules (NEVER break — they come from the law)

1. **Legal records are never deleted.** Soft-delete (`deleted_at`) everywhere;
   every query filters `WHERE deleted_at IS NULL`. 3-year retention.
2. **`treatment_date` = device timestamp**, never server `datetime.now()`
   (advisors record offline and sync hours later).
3. **Idempotency via `transaction_id`** (client-generated `crypto.randomUUID()`),
   UNIQUE constraint. Never via audio hash.
4. **LLM output is untrusted.** Every Qwen JSON goes through the Pydantic
   model `ExtractedFields` before touching the DB. Missing mandatory field →
   HTTP 422 with a clear Spanish message; never invent values.
5. **Legal validation before persisting:** product authorized · dose ≤
   `max_allowed_dose` · treated area ≤ `enclosure_area_ha`.
6. **Records belong to the HOLDING** (owner, NIF, REA/REGEPA number), not to
   the advisor. Chain: advisors → holdings → plots.
7. **State machine (M5+):** OBSERVATION (terminal) · PRESCRIBED → EXECUTED →
   ASSESSED. No backward transitions; corrections = new intervention +
   soft-delete of the old one.
8. **AEMET weather is captured when EXECUTION is confirmed** (real application
   date — use historical data if deferred), not when the prescription is
   recorded. If AEMET fails: save anyway with `audit_state='WEATHER_PENDING'`;
   never block the advisor.
9. UTC in the database; render `Europe/Madrid` only in PDFs.
10. DO NOT EVER READ .env. Secrets only in `config/.env` (gitignored). `.env.example` has empty values. 

## Domain glossary

- **GIP advisor**: certified technician who prescribes phytosanitary
  interventions and validates the holding's records.
- **ROPO**: official register of qualified persons (advisor and operator hold
  *different* ROPO numbers). **ROMA**: official register of the machine.
- **SIGPAC**: official plot identification (province/municipality/polygon/
  parcel/enclosure). The **enclosure** caps the legally treatable area.
- **REA/REGEPA**: the holding's official ID before the Administration.
- **CUE/SIEX**: digital holding logbook / Ministry system where records will
  be exported (post-MVP).
- **ITEAF**: mandatory periodic inspection of application equipment.
- **PHI (pre-harvest interval)**: minimum days between treatment and harvest
  (per product) → `earliest_harvest_date`.
- **Intervention**: central unit — an observation, prescription or execution.
- **Validation**: advisor's signed conformity over a holding's interventions;
  mandatory twice per campaign (mid-cycle + final).

## Code conventions

- Domain errors = typed exceptions (spec §5) → HTTP 422/404 as
  `{"error": "DOSE_ERROR", "mensaje": "<Spanish, readable by an agronomist>"}`.
- Commits in English, imperative, milestone-tagged:
  `[M1] add field extraction with Qwen Instruct`.
- The extraction prompt lives in `prompts/extraction_v1.md` (few-shot
  examples in Spanish — that's what the model will hear); every change bumps
  the version (`prompt_version` column).

## Decision context

This is a TFG (bachelor's thesis): when two options exist, prefer (1) code the
student can fully understand — explain the why of non-trivial choices — and
(2) the simple thing that works today over the elegant thing for tomorrow.
Log every decision (taken AND discarded) in `docs/decisions.md`, one line
each: what, why, date. That file becomes the thesis' design chapter.
