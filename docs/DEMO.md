# Demo — video script & screen-by-screen walkthrough

Part 1 is the shooting script for the Devpost demo video. Part 2 is a static
walkthrough a judge can read without running anything.

All screenshots live in `docs/img/` and were taken on a real Android phone
running the installed PWA. The dictated audio is in Spanish (that is what the
model is trained on with the few-shot prompt); translations are given inline.

**Demo phrase** (also shown by the app on the empty list, ready to dictate):

> *"Finca de Pepe, Abamectina 1,5 litros por hectárea, araña roja, tractor"*
> — "Pepe's farm, abamectin at 1.5 L/ha, red spider mite, tractor sprayer"

---

## Part 1 — Video script (target ≈ 2–3 min)

Record the phone screen (the whole demo runs on a real phone); voice-over on
top. Suggested takes:

| # | Time | Take | What to show / say |
| --- | --- | --- | --- |
| 1 | 0:00–0:20 | **Hook** | Title card / field photo. "On January 1st 2027, every farm in Spain must keep pesticide records electronically. The people who create them work in a field, with dirty hands. AgroVoz turns a 10-second voice note into the legal record." |
| 2 | 0:20–0:35 | **Login** | Installed PWA icon on the home screen → open → email → OTP code arrives → in. One sentence: "installable PWA, one-time code login — no passwords needed in the field. Judges can create their own trial account with demo data from the login screen." |
| 3 | 0:35–1:00 | **Record** | Big record button → dictate the demo phrase → playback card → "Transcribir y revisar" → staged progress (transcribing… extracting fields…). |
| 4 | 1:00–1:25 | **Review** | The two-phase flow: every extracted field prefilled, ✓ markers on catalog-resolved names (plot + SIGPAC + crop, product, equipment), editable before anything is saved. "Nothing from the LLM reaches the legal record unseen." |
| 5 | 1:25–1:40 | **Confirm → PDF** | Confirm → record appears in today's list → open detail → download the official PDF. "Voice in, legally valid PDF out, under a minute." |
| 6 | 1:40–2:00 | **The killer feature: it says no** | Edit the dose to 3 L/ha (or dictate an illegal one) → the red "Bloqueado por validación legal" card with the exact Spanish reason. Same with a treated area larger than the SIGPAC enclosure. "This is not a transcription toy — it refuses to persist an illegal record, down to unit conversion." |
| 7 | 2:00–2:20 | **Offline queue** | Airplane mode → record → the take lands in "Pendientes" with playback → coverage back → retry → same review flow, original timestamp. "The field has no signal; nothing is lost, nothing duplicates." |
| 8 | 2:20–2:40 | **Lifecycle** *(fast montage)* | Detail actions: confirm execution (weather captured), effectiveness assessment (voice-dictated reason), campaign validation screen with the 1/2 counter and its PDF. |
| 9 | 2:40–3:00 | **Close** | "Built solo, milestone by milestone, each one verified on a real phone. The 2027 deadline is not a threat — with the right tool, it's ten seconds of talking." Live URL + repo on screen. |

Tips:
- Takes 3–5 are one continuous phone recording — don't cut the moment the
  fields appear filled; that's the wow.
- Have the OTP email already open in take 2 (don't make judges watch an inbox).
- Pre-provision the demo catalog so every name resolves with ✓ (the trial
  account already ships with it).

---

## Part 2 — Screen-by-screen walkthrough

### Installed PWA

AgroVoz installs from the browser as a PWA and lives on the home screen like
any native app.

![AgroVoz PWA icon on the phone's home screen](img/apponphone.jpeg)

### Login (email OTP) + trial account

The advisor enters their email and receives a 6-digit one-time code; password
login is available as a secondary tab (set up in Ajustes). The form is
protected by a Cloudflare Turnstile check, and the privacy policy is linked
right below. There is no regular self-signup — advisor accounts are
provisioned by the admin — but the login screen offers **"Crear cuenta de
prueba"**: a judge can create a throwaway trial account pre-loaded with demo
catalog data (Pepe García's holding) and try the whole flow.

![Login — email OTP with password tab and trial-account link](img/login1.jpeg)

![OTP code entry after the email is sent](img/login2.jpeg)

![Trial account creation with demo data](img/register.jpeg)

### Home — record button + today's list

One big record button and today's records ("Hoy"). Each card shows the state
badge (Prescripción / Ejecución…), the plot and holding owner, the product's
trade name and the dose + target pest. The bottom bar navigates to Historial,
Validar, Ajustes and Salir.

![Home — record button and today's list](img/home.jpeg)

### Recording → playback → staged progress

The button turns red while recording ("Grabando — pulsa de nuevo para
terminar"). The take then appears as an audio player — the advisor can listen
before sending or discard it. "Transcribir y revisar" uploads the audio and
shows staged progress (transcribing → extracting fields) while the pipeline
runs; nothing is persisted yet.

![Recording in progress](img/recording.jpeg)

![The recorded take with playback, before sending](img/recorded.jpeg)

![Staged progress while the fields are extracted](img/recorded2.jpeg)

### Review before persist (two-phase flow, M8)

"Revisa antes de guardar": the transcription is quoted verbatim at the top,
the record type (Observación / Prescripción / Ejecución) is preselected, and
every extracted field comes back **prefilled but unsaved**. Identity fields
carry a resolution marker: ✓ means the dictated name was resolved against the
official catalog — the plot shows its crop and SIGPAC enclosure
(`Cítricos · SIGPAC 12:040:7:15:1`), product and equipment show "En el
catálogo". Everything is editable, and optional fields (treated area, spray
volume, operator + their ROPO, justification) can be completed by hand. Only
on "Confirmar y guardar" does the record go through legal validation and
persist.

![Review form with per-field resolution markers](img/review.jpeg)

### Blocked by legal validation

An illegal record is **blocked before persisting**, with the exact reason in
Spanish. Two real examples: a dose over the product's registered maximum
(after unit conversion), and a treated area larger than the SIGPAC
enclosure's legal area.

![Blocked — dose over the legal maximum for the product](img/blockedilegaldose.jpeg)

![Blocked — treated area exceeds the SIGPAC enclosure](img/blockedilegalarea.jpeg)

### Detail + actions

The detail screen shows every legal field (product, MAPA registration
number, dose, target pest), the holding block (owner, REA/REGEPA, SIGPAC),
and the verbatim transcription ("Lo que dictaste"). Below, the actions for
the record's state: prepare the prescription PDF, confirm execution, correct
(supersede) or delete (soft).

![Prescription detail with its actions](img/prescriptionactions.jpeg)

### Official PDF

"Preparar prescripción (PDF)" downloads the official document to the phone:
*Prescripción de tratamiento fitosanitario* under RD 1311/2012, with the
advisor's ROPO number, the holding (NIF, REA/REGEPA), the plot (crop, SIGPAC
enclosure, area), the prescribed treatment (active substance, MAPA
registration number, dose, target pest, equipment with its ROMA number, PHI)
and the advisor's signature line.

![Downloading the prescription PDF](img/pdfdownload1.jpeg)

![The official prescription PDF, RD 1311/2012 layout](img/pdfdownloaded.jpeg)

### Execution confirmation (FLUJO B)

"Confirmar ejecución" right on the detail: real application date, actual
dose, treated area, spray volume, operator and their ROPO, and the
delivery-note/invoice number — re-validated against the same legal rules.
Weather at the application time is captured automatically (Open-Meteo); if
the provider fails, the record saves as `WEATHER_PENDING` — the advisor is
never blocked.

![Execution confirmation form on the detail](img/confirmingexecution.jpeg)

### Effectiveness assessment (M6)

Once executed, the record can be assessed: Buena / Regular / Mala, assessment
date and an optional reason — typed or **dictated with the microphone**
("Dictar el motivo").

![Effectiveness assessment on an executed record](img/asessesingexecution.jpeg)

### Campaign validations (M7)

The advisor signs their conformity over a holding's records — mandatory twice
per campaign (mid-cycle + final). Grouped by holding with a per-campaign
counter (1/2 after the mid-cycle one): each validation shows its date, the
interventions covered and the verdict, and produces a validation PDF with the
advisor's conformity declaration (name + ROPO). The final sign-off asks
Conforme / No conforme with observations (dictable by voice too).

![Validations — holding card with the campaign 1/2 counter](img/validations.jpeg)

![Signing the end-of-campaign validation](img/signingvalidationfinal.jpeg)

### History

Full record history with quick ranges (this month / last 30 days / all) and a
custom from/to date filter.

![History with date-range filter](img/history.jpeg)

### Settings

Ajustes shows the logged-in account and lets the advisor set a password to
skip the OTP wait on future logins.

![Settings — set a password](img/settings.jpeg)

### Offline pending queue

A recording made without coverage (note the airplane-mode icon in the status
bar) is kept on the device (IndexedDB) with playback, under "Pendientes de
sincronizar" with its **original dictation timestamp** ("Dictada el…"). The
advisor retries or discards it manually once back in coverage; the retry
reuses the original idempotency key and device timestamp: nothing is lost,
nothing duplicates.

![Offline pending queue with the original dictation timestamp](img/indexeddbaudio.jpeg)
