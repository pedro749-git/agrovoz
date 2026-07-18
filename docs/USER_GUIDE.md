# User guide — every flow, with dictation examples

What the advisor (the only end user) can do in AgroVoz, flow by flow, with
real dictation phrases and every possible outcome. Dictation is always in
**Spanish** (that is what the extraction prompt is trained on); explanations
here are in English, with a gloss after each phrase.

Replaces the old `funcionabilidad.md` (Spanish, pre-M8).

---

## 1. Roles & onboarding

In the permanent design there is **no self-signup**. The admin validates and
provisions each advisor; the advisor only ever logs in.

1. **Admin validates the advisor (outside the system).** The advisor provides
   DNI, ROPO number and email; the admin checks the public ROPO registry
   (MAPA) — the advisor must be ACTIVE and hold the *Asesor* category
   (*Básico* is not enough).
2. **Admin creates the account** in Supabase: the auth user and the `advisors`
   profile (`account_status = 'ACTIVE'`), linked via `auth_user_id`.
3. **Admin provisions the catalog** the voice pipeline resolves against:
   - `holdings` — owner, NIF, REA/REGEPA number, default operator;
   - `plots` — SIGPAC identification + `voice_alias` (what the advisor calls
     it out loud) + centroid lat/lon;
   - `equipment` — ROMA number + `equipment_alias`.
   The advisor never types any of this.
4. **Advisor logs in** (next section).

> **Temporary hackathon exception — the trial account.** While the event
> lasts, the login screen offers *"Crear cuenta de prueba"*: a new user signs
> up and `POST /api/bootstrap` (behind the `hackathon_signup_enabled` flag)
> provisions a **throwaway demo advisor** with a personal sandbox catalog —
> the "Pepe García (demo)" holding, the plots *Finca de Pepe* (Cítricos) and
> *El Bancal* (Olivar), and the *tractor* equipment — so a judge can try the
> whole flow with the canonical demo phrase. With the flag off the endpoint
> returns 404 and the closed-login design applies unchanged.

## 2. Login

- **Primary**: email → Supabase sends a 6-digit one-time code → enter it.
- **Secondary**: email + password, once the advisor sets a password in
  *Ajustes*.
- The session persists; reopening the installed PWA goes straight to Home.

## 3. Recording an intervention (the main flow — FLUJO A)

From Home, the advisor taps the big record button and dictates a natural
voice note. **One button, three kinds of record** — the system classifies the
audio by its content:

| You dictate… | `record_type` | Stored state | PDF? |
| --- | --- | --- | --- |
| what you *see*, no product | `OBSERVATION` | `OBSERVATION` (terminal) | No — GIP surveillance, not a legal treatment |
| what should be *applied* ("hay que aplicar…") | `PRESCRIPTION` | `PRESCRIBED` | Yes — prescription PDF |
| what was *already applied* ("hemos echado…") | `EXECUTION` | `EXECUTED` (prescription+execution collapsed into one record) | — (execution record; weather captured) |

### 3.1 The two-phase flow (M8): nothing is saved unseen

1. **Preview** — the audio is transcribed (Qwen3-ASR-Flash) and the fields
   extracted (Qwen-Flash), then resolved against the official catalog.
   Transcription is biased toward the advisor's registered catalog names
   (plots, products, equipment), so proper nouns tend to be heard right the
   first time. Nothing is persisted yet.
2. **Review** — a form shows every field prefilled, with a **✓/⚠️ marker per
   identity field**: ✓ = the dictated name matched a registered plot /
   product / equipment (canonical name shown, plus the plot's crop and
   SIGPAC); ⚠️ = no confident match, needs your attention. Everything is
   editable.
3. **Confirm** — only now do the reviewed fields go through **legal
   validation** and, if they pass, get persisted (and the PDF generated).

The record's `treatment_date` is the **device timestamp at dictation time**,
never the server clock — dictating offline and syncing hours later keeps the
real time.

### 3.2 Phrasebook — what to say

Every phrase below uses the trial-account sandbox (§1) — plots *Finca de
Pepe* (Cítricos) and *El Bancal* (Olivar), equipment *tractor*, product
Abamectina — so each example is reproducible as-is in a demo account. The
error examples in §3.3 that deliberately use an unregistered name say so.

**Prescription (minimal — the four mandatory pieces: plot, product + dose,
pest, equipment):**

> *"Finca de Pepe, hay que aplicar Abamectina a uno con cinco litros por
> hectárea contra araña roja con el tractor"*
> — Pepe's farm, apply abamectin at 1.5 L/ha against red spider mite, with
> the tractor sprayer.

**Prescription (full — adds GIP justification, previous alternatives and a
planned date):**

> *"Finca de Pepe, umbral superado, prescribo Abamectina a uno coma cinco
> litros por hectárea contra la araña roja con el tractor; ya pusimos
> trampas sin éxito, previsto para el quince de agosto"*
> — Pepe's farm, threshold exceeded, I prescribe abamectin at 1.5 L/ha
> against red spider mite, with the tractor; we already tried traps without
> success, planned for August 15th.
> → `justification` "umbral superado", `previous_alternatives` "trampas sin
> éxito", `planned_date` filled.

**Observation (surveillance — no product, no dose):**

> *"En El Bancal he contado tres capturas en la trampa, está por debajo del
> umbral, de momento no hace falta tratar"*
> — El Bancal (the demo's olive plot), three catches in the trap, below
> threshold, no treatment needed for now.
> → stored as `OBSERVATION` with the note as `observation`; documents the
> GIP surveillance that later justifies a prescription.

**Direct execution (the treatment already happened — past tense):**

> *"En la Finca de Pepe hemos echado esta mañana Abamectina a uno con dos
> litros por hectárea contra araña roja, dos hectáreas tratadas con el
> tractor, lo aplicó Juan"*
> — Pepe's farm, this morning we applied abamectin at 1.2 L/ha against red
> spider mite, two hectares treated with the tractor, Juan applied it.
> → stored directly as `EXECUTED` with `treated_area_ha` 2 and
> `operator_name` "Juan"; weather is captured for the real application date.

**Dose units** — the model writes the unit exactly as dictated, in compact
form; it **never converts the number** (conversion is the validator's job):

| Dictated | Extracted |
| --- | --- |
| *"uno con cinco litros por hectárea"* | `dose: 1.5, dose_unit: "L/ha"` |
| *"dos kilos por hectárea"* | `dose: 2, dose_unit: "Kg/ha"` |
| *"doscientos mililitros por hectárea"* | `dose: 200, dose_unit: "ml/ha"` |
| *"medio hectolitro por hectárea"* | `dose: 0.5, dose_unit: "hl/ha"` — **not** 50 L/ha |
| *"veinte cc por hectolitro"* | `dose: 20, dose_unit: "cc/hl"` |
| *"tres litros por árbol"* (not a canonical unit) | kept literal: `"litros por árbol"` — the validator will refuse to guess |

### 3.3 Every possible outcome

**With connection (~10 s):**

| Outcome | Example trigger (dictated) | What the advisor sees |
| --- | --- | --- |
| ✅ Saved | any valid phrase above | Record in today's list; prescription → PDF link |
| 👁 Observation saved | the observation phrase | Surveillance record, no PDF |
| ⛔ `DOSE_ERROR` — over the legal max | *"Abamectina **cinco** litros por hectárea"* (registered max is 2.0 L/ha) | Blocked-by-legal-validation card: dose exceeds the registered maximum |
| ⛔ `DOSE_ERROR` — over the max **after unit conversion** | *"Abamectina **medio hectolitro** por hectárea"* (0.5 hl/ha = 50 L/ha) | Blocked — the validator converts to the catalog's unit before comparing |
| ⛔ `DOSE_ERROR` — unit not comparable / not recognized | *"tres litros **por árbol**"* | Blocked with *"indica la dosis en L/ha…"* — incomparable units are refused, never guessed |
| ⛔ `PRODUCT_ERROR` | *"…hemos echado **Clorpirifos** dos kilos por hectárea…"* — chlorpyrifos lost its EU approval in 2020 | Blocked: product not authorized — **if** the shared catalog registers it as unauthorized; if it is simply not loaded, the product fails to resolve instead (⚠️) |
| ⛔ `AREA_ERROR` | *"…**diez hectáreas** tratadas…"* — Finca de Pepe's SIGPAC enclosure is 2.5 ha | Blocked: treated area exceeds the enclosure's legal area |
| ⛔ `FIELD_ERROR` (HTTP 422) | *"Finca de Pepe, aplicar Abamectina contra araña roja con el tractor"* — **no dose** | Missing mandatory field, clear Spanish message; the system never invents a value |
| ⚠️ → ⛔ `PLOT_NOT_FOUND` | *"Finca de **Manolo**…"* (not registered) | ⚠️ on the review screen; confirming without fixing it is rejected |
| ⚠️ → ⛔ `EQUIPMENT_NOT_FOUND` | *"…con la **mochila nueva**"* (alias not registered) | Same: fix it on the review form (or have the admin register the alias) |
| ⏳ `WEATHER_PENDING` | direct execution while the weather provider is down | Saved anyway with `audit_state='WEATHER_PENDING'` — the advisor is never blocked |

**Without connection — the offline pending queue:**

- The take is stored **on the device** (IndexedDB) with its original device
  timestamp and a client-generated `transaction_id`.
- It appears in the **Pendientes** list with playback; sync is **manual**
  (retry or discard) — deliberate, because iOS Safari has no Background Sync
  API and auto-syncing would skip the human review step.
- The retry replays the same preview → review → confirm flow, reusing the
  original timestamp and idempotency key: **nothing is lost, nothing
  duplicates**.

## 4. Confirming an execution (FLUJO B)

A prescription is not a treatment. When the product has actually been
applied, the advisor opens the record's detail → **Confirmar ejecución**, a
short form where **every field is optional** and defaults to the prescribed
values: real dose (default: the prescribed one), treated area, spray volume
(default: the product's), operator name (default: the holding's default
operator) and operator ROPO.

On confirm, the system:

1. Re-runs **legal validation** on the real values (same dose/area caps).
2. Moves `PRESCRIBED → EXECUTED`.
3. Captures the **weather of the real application date** (Open-Meteo;
   historical data if confirmed days later). Provider down →
   `WEATHER_PENDING`, never a block. The gap stays recorded as
   `WEATHER_PENDING` — there is no automatic backfill yet (Open-Meteo serves
   historical data, so a later backfill is straightforward roadmap).
4. Computes `earliest_harvest_date` = real date + the product's pre-harvest
   interval (PHI).
5. Warns if the equipment's **ITEAF inspection has expired**.

## 5. Assessing effectiveness (FLUJO C)

Days later, on the follow-up visit, the advisor opens the executed record and
fills the assessment block:

- **Buena / Regular / Mala** (Good / Fair / Poor) → `effectiveness`;
- an optional **dictated reason** — tap the mic, speak, the transcription
  lands in an editable text field:
  > *"La araña ha remitido, quedan focos en la esquina norte, vigilar la
  > semana que viene"* — the mites receded, hotspots remain in the north
  > corner, re-check next week.
- optionally the **delivery-note / invoice number** (`delivery_note_number`).

Saving moves `EXECUTED → ASSESSED`. Without this assessment the record is
incomplete under Annex III of RD 1311/2012.

## 6. Correcting and deleting (M8.2 — the law says records never die)

From the detail screen:

- **Corregir** — opens the review form prefilled with the record's fields.
  Saving creates a **new intervention** that supersedes the old one (linked
  via `supersedes_intervention_id`) and soft-deletes the original. The
  replacement inherits the original's dictation timestamp, transcription and
  `created_at`, preserving the audit chain. Only available before execution —
  correcting an executed treatment would rewrite history.
- **Eliminar** — soft-delete only (`deleted_at`); the row stays in the
  database for at least the legal 3-year retention period (the regulation
  sets a minimum, not an expiry). Nothing is ever physically deleted from
  the PWA.

Attempting a backward state transition (e.g. re-confirming an executed
record) is rejected with `STATE_TRANSITION_ERROR`.

## 7. Lists and detail

- **Home** — today's records + the record button. The empty state shows a
  ready-to-dictate demo phrase. Each card shows the state badge, the
  product's trade name and the plot/owner.
- **Historial** — full list with a **date-range filter**
  (`GET /api/interventions?from=&to=`).
- **Detail** — one template whose sections depend on the state:
  - `OBSERVATION`: the dictated note (verbatim), no PDF, no dose;
  - `PRESCRIBED`: legal fields + PDF download + the execution form;
  - `EXECUTED`: real application data, weather, earliest harvest date, the
    assessment block;
  - `ASSESSED`: everything above plus the read-only assessment.
- Each advisor sees **only their own interventions** (backend scoping by
  `current_advisor_id`).

## 8. Campaign validations (M7 — the advisor's own legal duty)

The advisor must sign conformity over each holding's records **twice per
campaign**: mid-cycle (`MID_CYCLE`) and final (`FINAL`). In the *Validación*
screen, holdings are grouped with a **0/2 counter**.

For each validation the advisor declares:

- ✅ **Conforme** → `conformity = true`;
- ⚠️ **No conforme** → `conformity = false` + **mandatory remarks**
  (dictated via the mic or typed):
  > *"Falta el albarán del tratamiento del olivar y la dosis aplicada en la
  > parcela norte no coincide con la prescrita"* — the olive grove
  > treatment's delivery note is missing and the dose applied on the north
  > plot does not match the prescribed one.

Outcomes: a **validation PDF** carrying the advisor's conformity declaration
(name + ROPO, period covered, intervention count, conformity + remarks, the
period's intervention list — a printed declaration; cryptographic digital
signature is on the roadmap);
`REMARKS_REQUIRED` if *No conforme* without an explanation;
`VALIDATION_EXISTS` if that campaign+type was already validated;
`INVALID_CAMPAIGN` for a malformed campaign.

## 9. The documents

**A — Prescription PDF** (Annex III Part I, RD 1311/2012). Generated when a
prescription is registered; the advisor downloads it from the detail and
shares it with the farmer. Contains: prescription number, advisor (name, DNI,
ROPO), plot (SIGPAC, crop, variety, enclosure area), target pest, GIP
justification and previous alternatives, product (trade name, MAPA
registration number), dose + unit, planned date, pre-harvest interval.

**B — Execution record** (Annex III Part II + EU Regulation 2023/564). The
data captured when an execution is confirmed — the annotation that will feed
the CUE/SIEX digital logbook (export itself is post-MVP): plot + crop,
treated area, **real** treatment date, product + active substance +
registration number, applied dose, target pest, operator (name + ROPO),
equipment (type + ROMA number), weather conditions, delivery-note number.

**C — Campaign validation PDF** (MAPA instructions; min. 2 per cycle).
Generated when the advisor signs a validation; kept for inspection. Contains:
the advisor's conformity declaration (name + ROPO — printed, not a
cryptographic signature), holding (owner + REA/REGEPA), campaign +
type (mid-cycle/final), period covered, conformity + remarks, intervention
count and the period's intervention list.

## 10. What the advisor cannot do (by design, in the MVP)

- ❌ **Register plots, equipment or holdings** — the admin provisions them,
  guaranteeing correct SIGPAC, ROMA and REA/REGEPA identifiers.
- ❌ **Edit their professional data** (DNI, ROPO) — legally validated at
  onboarding; changes require re-validation.
- ❌ **Hard-delete interventions** — legal records; soft-delete only.
- ❌ **See other advisors' interventions** — scoped per advisor.
- ❌ **Export to the Government (SIEX/CUE)** — post-MVP, and an
  administrator's function, not the advisor's.
- ❌ **Self-signup** — a valid email is not enough; the ROPO check comes
  first. (Temporary exception: the hackathon **trial demo account** — see
  §1 — which provisions throwaway demo data, never a real advisor profile.)
