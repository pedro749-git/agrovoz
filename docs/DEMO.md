# Demo — video script & screen-by-screen walkthrough

Part 1 is the shooting script for the Devpost demo video. Part 2 is a static
walkthrough a judge can read without running anything.

All screenshots live in `docs/img/`. The dictated audio is in Spanish (that is
what the model is trained on with the few-shot prompt); translations are given
inline.

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
| 2 | 0:20–0:35 | **Login** | Installed PWA icon on the home screen → open → email → OTP code arrives → in. One sentence: "installable PWA, one-time code login — no passwords needed in the field." |
| 3 | 0:35–1:00 | **Record** | Big record button → dictate the demo phrase → staged progress messages (transcribing… extracting… validating). |
| 4 | 1:00–1:25 | **Review** | The two-phase flow: every extracted field prefilled, ✓ markers on catalog-resolved names (holding, plot + SIGPAC + crop, product, equipment), editable before anything is saved. "Nothing from the LLM reaches the legal record unseen." |
| 5 | 1:25–1:40 | **Confirm → PDF** | Confirm → record appears in today's list → open detail → download the official PDF. "Voice in, legally valid PDF out, under a minute." |
| 6 | 1:40–2:00 | **The killer feature: it says no** | Dictate an illegal dose (e.g. *"Abamectina 5 litros por hectárea"*) → the highlighted "blocked by legal validation" card with the Spanish error. "This is not a transcription toy — it refuses to persist an illegal record, down to unit conversion." |
| 7 | 2:00–2:20 | **Offline queue** | Airplane mode → record → the take lands in "Pendientes" with playback → coverage back → retry → same review flow, original timestamp. "The field has no signal; nothing is lost, nothing duplicates." |
| 8 | 2:20–2:40 | **Lifecycle** *(fast montage)* | Detail actions: confirm execution (weather captured), effectiveness assessment, campaign validation screen with the 0/2 counter and signed PDF. |
| 9 | 2:40–3:00 | **Close** | "Built solo, milestone by milestone, each one verified on a real phone. The 2027 deadline is not a threat — with the right tool, it's ten seconds of talking." Live URL + repo on screen. |

Tips:
- Takes 3–5 are one continuous phone recording — don't cut the moment the
  fields appear filled; that's the wow.
- Have the OTP email already open in take 2 (don't make judges watch an inbox).
- Pre-provision the demo catalog so every name resolves with ✓.

---

## Part 2 — Screen-by-screen walkthrough

### Login (email OTP)

The advisor enters their email and receives a 6-digit one-time code (password
login is available as a fallback, set up in Ajustes). There is no self-signup:
the admin provisions advisor accounts.

<!-- 📸 TODO: docs/img/login.png — login screen with the email field,
     plus the OTP code entry step -->
![Login — email OTP code](img/login.png)

### Home — record button + today's list

One big record button and today's records. The empty state shows a
ready-to-dictate demo phrase. Each card shows the state badge, the product's
trade name and the plot/owner.

<!-- 📸 TODO: docs/img/home.png — today's list with 2–3 records in different
     states (PRESCRIBED / EXECUTED); consider a second shot of the empty
     state with the demo phrase -->
![Home — record button and today's list](img/home.png)

### Recording → staged progress

While the audio is processed the advisor sees staged progress (transcribing →
extracting → validating).

<!-- 📸 TODO: docs/img/recording.png — recording in progress or the staged
     progress messages -->
![Recording with staged progress](img/recording.png)

### Review before persist (two-phase flow, M8)

The extracted fields come back **prefilled but unsaved**, with a ✓/⚠️ marker
per identity field: ✓ means the dictated name was resolved against the
official catalog (holding, plot with its SIGPAC enclosure and crop, product,
equipment); ⚠️ means it needs the advisor's attention. Everything is editable.
Only on confirm does the record go through legal validation and persist.

<!-- 📸 TODO: docs/img/review.png — review form with the ✓ markers and the
     plot's crop/SIGPAC visible. This is the most important screenshot after
     the hero GIF. -->
![Review form with per-field resolution markers](img/review.png)

### Blocked by legal validation

An illegal record — unauthorized product, dose over the registered maximum
(after unit conversion), area over the enclosure's legal area — is **blocked
before persisting**, with a clear message in Spanish.

<!-- 📸 TODO: docs/img/blocked.png — the highlighted "blocked by legal
     validation" card (e.g. after dictating a 5 L/ha dose of Abamectina) -->
![Record blocked by the legal validation engine](img/blocked.png)

### Detail + official PDF

The detail screen shows every legal field and the actions available for the
record's state: download PDF, confirm execution, assess effectiveness,
correct (supersede) or delete (soft).

<!-- 📸 TODO: docs/img/detail.png — detail of a PRESCRIBED record with its
     action buttons -->
![Intervention detail with actions](img/detail.png)

<!-- 📸 TODO: docs/img/pdf.png — the official PDF open on the phone -->
![Official prescription PDF](img/pdf.png)

### Execution confirmation (FLUJO B)

The advisor confirms the real application: actual dose, treated area, spray
volume and operator — re-validated against the same legal rules. Weather at
the application time is captured automatically (Open-Meteo); if the provider
fails, the record saves as `WEATHER_PENDING` — the advisor is never blocked.

<!-- 📸 TODO: docs/img/execution.png — execution confirmation form -->
![Execution confirmation](img/execution.png)

### Offline pending queue

A recording made without coverage is kept on the device (IndexedDB) with
playback, and manually retried or discarded from the "Pendientes" list. The
retry reuses the original idempotency key and device timestamp: nothing is
lost, nothing duplicates.

<!-- 📸 TODO: docs/img/pending.png — "Pendientes" list with a queued take -->
![Offline pending queue](img/pending.png)

### Campaign validations (M7)

The advisor signs their conformity over a holding's records — mandatory twice
per campaign (mid-cycle + final) — grouped by holding with a 0/2 counter, and
gets a signed PDF.

<!-- 📸 TODO: docs/img/validation.png — validation screen with the per-holding
     0/2 counter -->
![Campaign validation screen](img/validation.png)

### History

Full record history with a date-range filter.

<!-- 📸 TODO: docs/img/history.png — history screen with the date filter.
     Optional: drop this shot if the video already shows it. -->
![History with date-range filter](img/history.png)
