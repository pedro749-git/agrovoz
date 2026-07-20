# AgroVoz — the idea, in depth

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
| 1 · Surveillance | Field, all year — **~80% of visits** | Advice "must be documented" (art. 11.2), yet most visits end in *"don't treat"* and today that is written nowhere | ✅ **Observation audio** (~30 s, no product) — documents the GIP surveillance that justifies the next prescription |
| 2 · Prescription | Field, when a threshold is exceeded | Advisor's prescription → record of interventions (Annex III) → handed to the farmer | ✅ **Prescription audio** → PDF carrying their name and ROPO in seconds, with unauthorized product / illegal dose / over-area **blocked before reaching paper** |
| 3 · Execution | Done by the **farmer**, not the advisor | Annotation of the real application (the future CUE/SIEX entry, EU 2023/564) | ✅ **Execution confirmation**: real date/dose/operator → weather of the *real* application date → earliest harvest date (PHI) |
| 4 · Follow-up | Field, days later | Result of the treatment | ✅ Effectiveness (Good/Fair/Poor) + delivery-note number on the detail screen |
| 5 · Validation | Twice per crop cycle — **mandatory** | The advisor formally declares conformity over the record, mid-cycle and at closing | ✅ **One button**: validation PDF with the period's interventions + conformity declaration (name + ROPO) |
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
| Target pest + GIP justification + previous alternatives | Annex III / MAPA doc | Voice (dictated in the same note) |
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
- ⚙️ **System** — catalog lookups, earliest harvest date, ITEAF warning,
  prompt version.
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
