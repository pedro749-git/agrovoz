# AgroVoz — the idea, in depth

Two parts. **Part 1** is the Devpost submission story (copy everything from
`## Inspiration` down into the form; before submitting, confirm the "deployed
on Alibaba Cloud ECS" line matches reality). **Part 2** goes deeper: the
advisor's real working year, the regulation that shapes the design, and why
the data model looks the way it does. Distilled from the original Spanish
specification (in git history as `docs/mvp_asesor_gip_v3.md`).

---

# Part 1 — The story (Devpost)

## Inspiration

On **January 1, 2027**, every farm in Spain must keep its phytosanitary (pesticide) treatment records electronically — Spanish RD 1311/2012 and EU Regulation 2023/564 (as amended) make it mandatory. But the people who create those records, certified GIP (Integrated Pest Management) advisors, work standing in a field with dirty hands and no time for forms. Today they scribble notes and reconstruct the legal record at night, from memory. Errors in that record are not typos — they are legal liabilities.

Then I realized something: a 10-second voice note — *"Pepe's farm, red spider mite, abamectin at 1.5 liters per hectare, tractor sprayer"* — already contains everything the law requires. The missing piece wasn't data entry. It was a translator between how advisors actually talk and what the regulation demands.

## What it does

AgroVoz turns a dictated field note into a legally valid phytosanitary record:

1. The advisor records a short audio in Spanish from a PWA on their phone.
2. **Qwen3-ASR-Flash** transcribes it; **Qwen-Flash** extracts structured fields (plot, product, dose, target pest, equipment) as JSON.
3. Dictated names are resolved against official catalogs — the advisor says *"la finca de Pepe"*, the system finds the registered holding, plot and SIGPAC enclosure.
4. A **legal validation engine** checks the record before anything is saved: product authorized for that crop, dose ≤ the registered maximum (with unit conversion), treated area ≤ the enclosure's legal area, pre-harvest interval computed.
5. The advisor reviews a screen with per-field ✓/⚠️ markers, confirms, and gets the official PDF — stored, signed-off and downloadable.

If there is no signal in the field, the take is queued locally (IndexedDB) and shows up as "pending to sync" — retrying it replays the same review flow with the original device timestamp, so nothing is lost and nothing duplicates.

It also covers the full legal lifecycle: prescription → execution confirmation (with weather captured at application time), effectiveness assessment, twice-per-campaign advisor validations, and corrections that **never delete** a legal record (supersede + soft-delete, as the 3-year retention rule requires).

## How we built it

Solo project, built in strict incremental milestones (M1–M8), each one working end-to-end on a real phone before starting the next — from a throwaway spike that proved Qwen could understand a Spanish field advisor, to the full state machine.

- **Backend:** Python 3.12 + FastAPI, hexagonal architecture (ports & adapters), Pydantic V2 everywhere.
- **AI:** Qwen3-ASR-Flash (speech→text) + Qwen-Flash (text→JSON) via DashScope, with versioned few-shot prompts written in field Spanish.
- **Data & infra:** Supabase (PostgreSQL + OTP auth), Alibaba Cloud OSS for audio and PDFs, ReportLab for the official documents, deployed on Alibaba Cloud ECS.
- **Frontend:** React + Vite + Tailwind PWA — installable, one big record button, offline queue for dead zones.

## Challenges we ran into

- **LLM output is untrusted input.** Early on, the model happily invented plausible doses. Every extraction now passes through a strict Pydantic schema; a missing mandatory field returns a clear error in Spanish instead of a guessed value.
- **Unit-blind dose validation.** The advisor says "0.5 hl/ha"; the catalog registers the limit as "1.5 L/ha". Naively comparing numbers silently approves an illegal dose — I built unit normalization into the validator, converting the dictated dose to the catalog's unit and **blocking** incomparable units instead of guessing.
- **People don't talk like databases.** Resolving *"la finca de Pepe"* to the right registered holding required a canonicalization step with per-field resolution markers, so the advisor sees exactly what was matched and what needs review.
- **The field has no signal — and iOS has no Background Sync.** Failed uploads queue in IndexedDB with the original device timestamp and a client-generated transaction ID (retries can never duplicate a legal record). Sync is deliberately manual: iOS Safari lacks the Background Sync API, and auto-syncing would skip the human review step.
- **iPhone PWA auth.** Magic links open in a different browser than the installed PWA and the session lands in the wrong place — I had to switch to email OTP codes.
- **The law as a state machine.** No backward transitions, no deletions: modeling corrections as a new record that supersedes the old one (inheriting the original treatment date and transcription for the audit chain) took several design iterations.

## Accomplishments that we're proud of

- The full pipeline works on a real phone in the field: **voice in, legally validated PDF out, in under a minute** — even from a dead zone, via the offline queue.
- The legal validation engine — this is not a transcription toy; it refuses to persist an illegal record, down to the unit conversion.
- The complete record lifecycle (observation, prescription, execution, assessment, campaign validation) with legal traceability.
- Built solo by a 3rd-year CS student — it is also my bachelor's thesis (TFG) — with every milestone verified end-to-end before moving on.

## What we learned

- Treat an LLM like a user typing into a form: validate everything, trust nothing, never let it invent.
- Regulation is an excellent spec — the official record's mandatory fields *are* the data model.
- Hexagonal architecture pays off even solo: swapping the weather provider or storage backend touches one adapter.
- Prompts are code: version them like schema migrations, keep one test per edge case.
- Shipping a working slice every milestone beats building a perfect architecture that never runs.

## What's next for AgroVoz — Voice-to-Legal Pesticide Records

- **The full official MAPA product registry** — turning the pilot catalog into the complete national database of authorized products, doses and pre-harvest intervals.
- **SIEX/CUE export** — pushing records directly into the Ministry's digital holding logbook, where they'll be legally required to live.
- **Rolling out to more advisors** — the schema and row-level security policies are already multi-tenant; what's left is the onboarding tooling (today the admin registers advisors and their catalogs by hand) and digital signature for campaign validations.

The 2027 deadline is not a threat to farmers — with the right tool, it's ten seconds of talking.

---

# Part 2 — The idea in depth

## The regulatory clock

| When | What |
| --- | --- |
| Today (mid-2026) | Paper records still valid (until 2026-12-31) — the adoption window |
| **2027-01-01** | Electronic phytosanitary records **mandatory** in Spain (Commission Implementing Regulation (EU) 2025/2203 + RD 1039/2025) |
| 2028-01-01 | Full CUE (digital holding logbook) for larger holdings (RD 1054/2022) |

The norms that shape the design:

- **RD 1311/2012** — the Spanish GIP framework. Arts. 10–15: the advisory
  duty; Art. 16 + **Annex III**: the treatment record. Its mandatory fields
  *are* AgroVoz's data model.
- **Commission Implementing Regulation (EU) 2023/564** — content and
  electronic format of the record; **3-year retention** (hence soft-delete
  everywhere, never a hard delete). Shortened to "EU 2023/564" elsewhere.
- **MAPA GIP advisory document** — the advisory contract, the holding
  description and the record-of-interventions templates, plus the rule that
  the advisor must validate the record **at least twice per crop cycle**
  (mid-cycle + final) — that is the campaign-validation feature.
- **RD 1702/2011** — periodic ITEAF inspection of application equipment
  (hence the expiry warning at execution time).

Three legal facts drive the whole design:

1. **The record belongs to the holding** (owner, NIF, REA/REGEPA number),
   not to the advisor — chain `advisors → holdings → plots`.
2. **Prescribing ≠ executing ≠ validating.** The record is not a snapshot,
   it is a lifecycle — hence the state machine
   (`OBSERVATION` · `PRESCRIBED → EXECUTED → ASSESSED`, no backward
   transitions; see [`ARCHITECTURE.md`](ARCHITECTURE.md)).
3. **Well-kept advisory documentation already satisfies the Art. 16
   record** — so a tool for the advisor's own paperwork produces, as a side
   effect, the farm's legal record.

## The advisor's year — and which pain AgroVoz picks

Each phase of the advisor's real work (per the official MAPA advisory
document) has a concrete pain. AgroVoz attacks the ones that happen **in the
field**, where paper hurts most:

| Phase | Where | The legal duty | AgroVoz |
| --- | --- | --- | --- |
| 0 · Contract + holding description | Office, once a year | Advisory contract + holding description (MAPA Annexes I–II); 1–2 h of start-of-campaign paperwork per client | ❌ Out of scope — the data already lives in the DB; generating these two PDFs with one button is post-MVP roadmap #1 |
| 1 · Surveillance | Field, all year — **~80% of visits** | Advice "must be documented" (art. 11.2), yet most visits end in *"don't treat"* and today that is written nowhere | ✅ **Observation audio** (~30 s, no product) — documents the GIP surveillance and automatically becomes the *previous alternatives* of the next prescription |
| 2 · Prescription | Field, when a threshold is exceeded | Advisor's prescription → record of interventions (Annex III) → handed to the farmer | ✅ **Prescription audio** → PDF signed with their ROPO in seconds, with unauthorized product / illegal dose / over-area **blocked before reaching paper** |
| 3 · Execution | Done by the **farmer**, not the advisor | Annotation of the real application (the future CUE/SIEX entry, EU 2023/564) | ✅ **Execution confirmation**: real date/dose/operator → weather of the *real* application date → earliest harvest date (PHI) |
| 4 · Follow-up | Field, days later | Result of the treatment | ✅ Effectiveness (Good/Fair/Poor) + delivery-note number on the detail screen |
| 5 · Validation | Twice per crop cycle — **mandatory** | The advisor formally declares conformity over the record, mid-cycle and at closing | ✅ **One button**: signed PDF with the period's interventions + conformity declaration (name + ROPO) |
| 6 · Retention | 3 years (EU 2023/564) | Keep everything available for inspection | ✅ Soft-delete + PDFs in OSS + audit trail |

**The problem in one sentence:** the advisor spends more time being a clerk
than an agronomist. AgroVoz turns every field-side documentation duty into
≤30 seconds of voice, with legality validated before anything touches paper.

## The law as a data model

The official record's mandatory-field checklist is the schema. Every column
exists because a norm demands it, and every mandatory field has exactly one
source:

| Official field | Required by | How AgroVoz captures it |
| --- | --- | --- |
| Holding owner (name, NIF) + REA/REGEPA | EU 2023/564 / RD 1054/2022 | Admin onboarding (`holdings`) |
| Advisor (name, ROPO number) | MAPA doc / art. 12 RD 1311/2012 | Admin onboarding, ROPO verified against the public registry |
| Full SIGPAC reference, crop, variety | Annex III / EU 2023/564 | Admin onboarding (`plots`), resolved from the dictated *voice alias* |
| Treated area (≤ enclosure) | Annex III / EU 2023/564 | Voice or execution confirmation — validated against the enclosure's legal area |
| Real application date (and time) | EU 2023/564 | Execution confirmation; always the **device** timestamp |
| Product: trade name + MAPA registration number | Annex III / EU 2023/564 | Voice → catalog lookup |
| Applied dose | EU 2023/564 | Voice / confirmation — validated ≤ legal max, unit-converted |
| Target pest + GIP justification + previous alternatives | Annex III / MAPA doc | Voice; alternatives auto-fed from the plot's recent observations |
| Operator identity + ROPO card | Annex III | Voice, or the holding's default operator |
| Equipment + ROMA number + ITEAF inspection | Annex III / RD 1702/2011 | Voice → catalog lookup; expiry warning computed |
| PHI → earliest harvest date | Product label (EU 1107/2009) | Computed: real date + the product's PHI |
| Delivery note / invoice number | FEGA | Follow-up (phase 4) |
| Effectiveness | GIP good practice | Follow-up (phase 4) |
| Advisor validation ×2 per cycle | MAPA doc | The validations feature (phase 5) |
| 3-year retention | EU 2023/564 | Soft-delete + OSS |
| Weather at application | Good practice (not mandatory) | Automatic (Open-Meteo), `WEATHER_PENDING` fallback |

Where every datum comes from, in one glance:

- 🎙️ **Voice** — record type (classified by the LLM), plot alias, product,
  dose + unit, pest, equipment, and optionally area, justification, operator,
  planned date.
- 📱 **Device** — idempotency `transaction_id`, the dictation timestamp, GPS.
- ⚙️ **System** — catalog lookups, previous alternatives, earliest harvest
  date, ITEAF warning, prompt version.
- 🌦️ **Weather provider** — at execution confirmation, for the real date.
- 🖥️ **Admin** — the trusted registers: holdings, plots (SIGPAC), equipment
  (ROMA, ITEAF), product catalog. The advisor never types identifiers.

## Deliberately out of scope (MVP)

- Phase 0 documents (advisory contract + holding description) — their data
  already lives in the DB; one-button generation is roadmap #1.
- SIEX/SgaCex export — roadmap #2; the execution annotation is already
  CUE-shaped, so export is a transformation, not a migration.
- Treated seeds, post-harvest treatments and storage facilities.

## The payoff, in numbers

A typical GIP advisor manages 30–60 holdings: Monday–Thursday in the field,
Friday reconstructing paperwork from memory. AgroVoz turns those 4–6 weekly
administrative hours into ~10 minutes of voice, and along the way: (1) the
invisible surveillance work becomes defensible documentation, (2) the legal
numbers cannot be wrong, (3) the two per-cycle validations are signed with
one button, and (4) when the electronic record becomes mandatory
(2027-01-01), the SIEX export is a transformation — not a migration.
