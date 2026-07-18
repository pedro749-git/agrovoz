# Design decisions log

One entry per decision (taken AND discarded): what · why · discarded
alternatives · date. Newest first — new entries go at the top. This file
becomes the thesis' design chapter.

## 2026-07-18 — Docs reorganization + audits for the hackathon

- Docs reorganized for the hackathon: README rewritten judge-first (hook,
  live-demo + hero-GIF placeholders, Mermaid pipeline, compressed milestone
  table) with the detail split into docs/ARCHITECTURE.md (diagrams, hard
  rules, API surface), docs/SETUP.md (install/run/tests, moved out of the
  README) and docs/DEMO.md (video script + screen walkthrough with 📸
  placeholders in docs/img/) · project renamed AgroVoz across docs to match
  the Devpost/PWA brand · 2026-07-18
- funcionabilidad.md replaced by docs/USER_GUIDE.md (English): every flow
  with Spanish dictation phrases (grounded in prompts/extraction_v2.md) and
  the full outcome matrix per flow · outdated claims dropped rather than
  translated — AEMET (now Open-Meteo), auto-sync on reconnect (queue retry is
  deliberately manual), weather on observations (hard rule 8: execution
  only), and the plots/map screens that were never built · 2026-07-18
- mvp_asesor_gip_v3.md merged with devpost_about.md into docs/ABOUT.md
  (English): part 1 = the Devpost story verbatim (still copy-pasteable into
  the form), part 2 = the spec's idea/regulatory content distilled (advisor's
  year, regulatory clock, law-as-data-model checklist, scope) · the spec's
  implementation sections (SQL, code, endpoints, screens, milestone plan)
  were dropped, they live in supabase/, ARCHITECTURE.md, USER_GUIDE.md and
  the README · original Spanish spec archived at docs/historico/ (TFG
  material, same pattern as the M1 spike); CLAUDE.md pointers updated ·
  2026-07-18
- Archived Spanish spec deleted from docs/historico (git history keeps it);
  Supabase migration comments cleaned for the public repo: initial migration
  translated to English, SQL-Editor box header / "changes vs original" block /
  stray terminal escape codes removed, AEMET mentions generalized to the
  weather provider; M6/M8.2 migrations were already in English · 2026-07-18
- Docs audit for the hackathon: SETUP test table completed (correction/
  reportlab tests were missing) · ARCHITECTURE gained correction_service +
  onboarding_service (diagram and layout) and the state diagram now shows the
  direct-EXECUTION entry with GitHub-safe labels (no <br/> in stateDiagram
  transitions) · CLAUDE.md realigned with reality: AgroVoz in the title,
  Open-Meteo instead of AEMET (stack, hard rule 8, adapter filename in the
  layout), services list completed, prompt pointer now v2 · sample PDFs are
  gitignored, so they are NOT linked from the README (discarded idea) ·
  full test suite green after the comment-only code touches (114 passed) ·
  2026-07-18
- External-audit fixes (second docs pass): USER_GUIDE's direct-execution
  example no longer uses Clorpirifos (EU approval withdrawn in 2020, and
  authorized=FALSE in the seed catalog — it would be blocked by our own
  validator); Clorpirifos is now deliberately the PRODUCT_ERROR example ·
  2023/564 and 2025/2203 named as Commission Implementing Regulations in
  ABOUT part 2, and part 1 says "as amended" for the 2027 date · identity
  unified everywhere as "3rd-year CS student's bachelor's thesis (TFG)" ·
  SETUP gained the missing schema step (supabase link + db push, or SQL
  Editor paste) · DEMO take 7 (offline queue) no longer optional · Devpost
  "we" headings kept as-is: they are Devpost's fixed form-section names,
  the body already speaks in first person singular · 2026-07-18
- Third docs pass (decisions.md + CLAUDE.md audit): decisions.md header now
  promises "one entry per decision" (the real, richer format) instead of one
  line, same fix in CLAUDE.md's Decision context · the 2026-06-30 "M5 step
  4a" section moved above the 06-29 sections to restore reverse-chronological
  order in the top zone · README no longer labels decisions.md as Spanish
  (it is English) · CLAUDE.md realigned: hardening phase added to the
  milestone checklist, hard rule 5 now states the unit conversion, the legal
  line carries the full amendment chain (2023/564 as amended by 2025/2203 +
  RD 1039/2025), identity unified as "3rd-year CS student's bachelor's
  thesis (TFG)" · KNOWN GAP, deliberately not fixed today: the file has two
  ordering zones (old top zone newest-first; entries since ~2026-07-06
  appended at the bottom oldest-first) — normalizing 1300 lines of thesis
  material deserves its own careful pass · 2026-07-18
- decisions.md normalized to one reverse-chronological convention (it had
  two zones: the original newest-first sections on top, and sessions since
  ~2026-07-06 appended oldest-first at the bottom) · loose session bullets
  grouped under dated "## date — title" headers, bullet text untouched
  (verified by line-multiset comparison) · header and CLAUDE.md now state
  the order (newest first) so future sessions prepend instead of appending ·
  2026-07-18

## 2026-07-17 — Pre-hackathon polish session (RGPD, brand, PWA)

- Signup code-step copy made generic ("Introdúcelo para continuar: crearemos
  tu cuenta o, si tu correo ya tenía una, iniciaremos sesión con ella", button
  "Continuar") · Supabase's signInWithOtp(shouldCreateUser) silently sends a
  plain LOGIN code when the email already has an account, so the old "Crear
  cuenta y entrar" copy lied to returning users, who ended inside their old
  account believing they had created a new one · DISCARDED detecting the case:
  (a) pre-send probe with shouldCreateUser:false lets anyone enumerate
  registered emails from the signup form (the very leak the password login
  avoids) and clashes with the single-use Turnstile token, which the
  retry-with-create call would burn twice; (b) post-verify `created:false`
  flag from /api/bootstrap + notice screen warns too late and adds a backend
  field + an App screen for a TEMPORARY hackathon flow — honest copy that
  covers both cases costs two strings and zero code · 2026-07-17
- RGPD privacy notice added (static /privacidad page + "Al continuar aceptas
  la política de privacidad" line under the login/signup card) · the app
  handles real personal data (email, voice audio sent to DashScope, third-party
  names/NIF/ROPO inside records) and its whole pitch is legal compliance, so
  shipping with zero RGPD surface was incoherent · the notice is
  prototype-honest: names the real processors (Supabase, Alibaba Cloud OSS +
  DashScope with possible non-EEA transfer, AEMET/Open-Meteo coordinates only),
  legal bases 6.1.b (service) and 6.1.c (RD 1311/2012 3-year retention — which
  is why deletion is soft, tying hard rule 1 to art. 17's legal-obligation
  limit), and warns not to enter real third-party data in a demo · DISCARDED
  for now: consent checkbox (friction for judges — the inline line suffices for
  a demo; a real deployment would add it), cookie banner (only strictly
  necessary storage: session + offline queue), formal RGPD paperwork (RAT,
  processor DPAs, transfer impact assessment — for when there is a real user) ·
  route is public in both router branches so the logged-out login screen can
  link it · 2026-07-17
- Desktop polish pass on the PWA · brand casing unified as "AgroVoz" (AppBar,
  login, manifest, privacy page) · every interactive element got a hover state
  with one consistent language per kind — solid olive buttons darken
  (hover:bg-olive-d), tinted chips deepen their tint (/10→/20), plain text
  links underline, AppBar icon buttons gain the same soft white wash their
  active state uses, record cards tint their border — because the demo is also
  judged on desktop, where only 4 of 15 components had any pointer feedback ·
  dropped the decorative leaf marks on the login card and the empty today-list
  (the AppBar already carries the brand; the empty state's job is the example
  phrase, not decoration) · "Historial" link restyled as a tinted chip, same
  recipe as the detail screen's action chips · 2026-07-17
- Login turned into a cover page: AppBar removed there and replaced by a brand
  block — a spoken-word waveform (7 uneven bars, olive opacity ramp fading at
  the edges; uneven on purpose, real speech is not a symmetric equalizer) over
  a big "AgroVoz" wordmark ("Voz" in the olive gradient) and the tagline · the
  leaf mark's removal had left the screen bare, and keeping the AppBar would
  have printed the brand twice on one screen; the waveform ties the mark to
  the product's core gesture (dictating) instead of generic agro imagery ·
  2026-07-17
- Detail-screen actions restyled from a pile of tinted chips (each its own
  width/colour, ragged left) into an "Acciones" section matching the screen's
  card language: one bg-card rounded-2xl card of full-width ActionRow rows
  (tinted icon tile in the action's semantic tone + soil label + chevron,
  delete in terra), dividers via divide-y — which works because every action
  component renders a single root whether collapsed or expanded, so the
  expanding confirm/assess forms open inside the card under their own bold
  title · discarded a solid primary CTA + secondary links (hierarchizes
  actions that are peers) and merely equal-width chips (still a foreign colour
  block on that screen) · 2026-07-17
- Removed the permanent hint under the record button ("Dicta una observación o
  una prescripción…") · it duplicated what the button (REGISTRAR + mic) and
  the empty today-list's example phrase already teach, overloading the home
  with text · the recording-state hint ("Pulsa de nuevo para terminar") stays:
  it only shows mid-action and teaches the one non-obvious gesture, that the
  same button stops · 2026-07-17
- Replaced the app icon/favicon — it was still Vite's template purple bolt
  (favicon.svg + both manifest PNGs), i.e. a foreign brand on the browser tab
  and the installed-app icon · new mark = the login's waveform on the olive
  gradient: favicon.svg hand-written, PNGs (192/512) drawn with Pillow
  full-bleed with the bars inside the maskable safe zone so one file serves
  the `any` and `maskable` purposes · already-installed PWAs keep the old
  icon until reinstalled · 2026-07-17
- Replaced the two window.confirm() dialogs (discard pending take, delete
  record) with an in-app ConfirmDialog (backdrop + card in the app's visual
  language, terra confirm button) · the native dialog broke the demo's look
  and leaks the site URL in its title; the two-step guarantee for destructive
  actions is unchanged — the action only runs from the dialog's confirm ·
  2026-07-17
- ReviewForm gained the execution-only fields (caldo, aplicador, ROPO del
  aplicador), shown only when record_type is EXECUTION · they existed in
  ExtractedFields and rode along uneditable, so a directly-dictated execution
  (or a correction switched to Ejecución) could not fix a mis-heard operator
  or spray volume in review — FLUJO B's confirm form covered only the
  prescription→execution path · same labels as that form; backend unchanged
  (fields were already optional in the schema) · 2026-07-17

## 2026-07-15 — Pre-hackathon hardening: offline queue, unit-aware doses, list names

- Offline pending queue (manual retry) in the PWA · the M4 "offline queue" idea,
  finally built minimal for the hackathon: when preview/commit cannot reach the
  server (fetch TypeError / navigator.onLine false — an HTTP 422 is NOT queued,
  the server answered), the take (blob + transactionId + deviceTimestamp, the
  exact trio hard rules 2/3 demand a retry to reuse) is parked in IndexedDB
  (`pendingTakes.js`, hand-rolled ~70-line wrapper, no new dependency) and Home
  shows a "Pendientes de sincronizar" section with per-take playback, Reintentar
  (feeds the take back into the Recorder via useImperativeHandle — an event, not
  a prop — and replays the normal M8 preview → review → commit flow) and
  Descartar (confirm dialog; legal because a pending take never reached the
  server, so it was never a record) · retry is MANUAL, not Background Sync:
  the API doesn't exist on iOS Safari (the reference device) and auto-sync
  would have to skip the M8 human review · IndexedDB here is best-effort
  storage (Safari may evict after ~7 days idle): a same-day sync buffer, not
  an archive — accepted · 2026-07-15
- Dose validation made unit-aware (bug: it compared raw numbers, so 0.5 hl/ha
  slipped past a 1.5 L/ha max) · two layers: prompt v2 gives Qwen the canonical
  unit vocabulary and forbids converting magnitudes (a conversion mistake by the
  LLM would silently write an illegal record — rule 4), while the backend keeps
  the guarantee: `validation_service` normalizes both units (synonyms table +
  hl/ml/cc/g factors, physical constants — no DB column), converts the dictated
  dose to the catalog's unit and compares there · unknown units and incomparable
  denominators (/hl spray concentration vs /ha surface — needs the spray volume)
  are BLOCKED with a Spanish DoseError asking for the catalog's unit: the app
  never certifies what it cannot check, never guesses · rejected alternative:
  prompt-only fix (LLM output is untrusted, and the advisor can hand-edit the
  unit in the review form) · 2026-07-15
- List cards enriched with the names the advisor recognises (product trade
  name, plot alias, holding owner) · the intervention row only stores the MAPA
  number + ids, and resolving names like the detail endpoint does (4 reads per
  record) would be N+1 over a 500-row history · chosen: three BATCH lookups over
  the distinct ids (`list_plots_by_ids` / `list_holdings_by_ids` /
  `list_products_by_registration_numbers`, PostgREST `.in_()`), so the whole
  list costs 3 extra queries regardless of size; missing rows degrade to null
  names, never break the list · the PWA card shows the trade name (MAPA number
  as fallback) and a "Finca de Pepe · José Ruiz" context line · 2026-07-15

## 2026-07-13 — M8.2 — soft-delete + correction by supersede (hard rules 1/7)

- CORRECTION = SUPERSEDE, never an in-place edit: a new intervention is committed
  with the corrected fields and the old row is soft-deleted. Editing the row
  (UPDATE) was DISCARDED — it destroys what the record said when its PDF was
  generated, breaking rule 1; supersede keeps both versions in the DB while the
  app only sees the live one (every read already filters deleted_at IS NULL).
- NEW COLUMN interventions.supersedes_intervention_id (UUID, self-FK, NULL unless
  the row is a correction). Debated against the "no speculative DB fields" rule
  and KEPT: without the link a corrected record and its soft-deleted predecessor
  are unrelated rows, so an audit cannot distinguish a correction from a plain
  deletion — the column is what makes rule 7 verifiable IN the data, i.e. a
  pipeline need, not speculation. Corrections form an auditable chain.
- CorrectionService.supersede REUSES pipeline.commit wholesale (no new insert
  path): the corrected fields are untrusted client input like any commit body, so
  they re-run ExtractedFields + catalog resolution + legal validation + the
  prescription PDF for free. Order is commit FIRST, soft-delete AFTER: a 422 on
  the corrected fields leaves the original untouched; a soft-delete failure after
  a successful commit self-heals on retry (commit's transaction_id idempotency
  returns the saved replacement, then only the soft-delete re-runs).
- The replacement INHERITS from the old record its raw_transcription (the audit
  trail documents what was DICTATED; a correction edits fields, not audio) and its
  ORIGINAL device timestamp (prescription_date ?? treatment_date ?? created_at) —
  sending a fresh device_timestamp was DISCARDED because a Thursday correction of
  a Monday prescription must not move the field event to Thursday (rule 2). So
  POST /api/interventions/{id}/correction carries only fields + transaction_id.
- The replacement ALSO inherits the old row's created_at (user decision, same
  day): with a DB-stamped created_at the correction jumped to "today" in the
  Home/history lists AND moved into a different campaign validation period (M7
  counts interventions by created_at window) — a correction must not relocate
  the intervention. Alternatives DISCARDED: grouping lists by prescription_date
  ?? created_at (does not cover OBSERVATIONs, needs an ugly PostgREST or-filter)
  and keeping the status quo (the campaign-period drift kills it). _serialize
  now sends created_at ONLY when explicitly set (fresh records keep the DB
  default); the correction moment is not lost — it lives in the old row's
  deleted_at.
- Lost-response retry on supersede: the first attempt soft-deleted the old row, so
  the retry's get_intervention(old_id) is None and would 404 a correction that
  SUCCEEDED; before raising, look up the (client-reused) transaction_id and return
  the replacement if it exists — same idempotency promise as commit (rule 3).
- DELETE /api/interventions/{id} = soft-delete in ANY lifecycle state (annulling a
  mistaken record is legitimate; the row persists for the 3-year retention either
  way), scoped to the advisor → unknown/foreign/already-deleted ids are the same
  404. Returns 204 (nothing to say about a now-invisible record).
- PWA offers "Corregir" only on OBSERVATION/PRESCRIBED for now: correcting an
  EXECUTED record through FLUJO A commit would drop its captured weather + real
  applied data (commit never calls Open-Meteo) — that slice waits until needed.
  "Eliminar" (native confirm()) is offered in every state. The correction screen
  REUSES ReviewForm prefilled from the detail; the detail endpoint/presenter now
  also joins the product row (trade_name) because the record stores only the MAPA
  number while commit resolves the product BY name — shown on the detail too
  ("Producto: Abamectina" above the MAPA number).

## 2026-07-13 — npm supply-chain hardening (pwa/.npmrc)

- npm supply-chain hardening in pwa/.npmrc · audit vs the 2026 npm attacks found
  nothing compromised (no flagged package/version in the 505-package lockfile,
  zero deps declaring install scripts, no attack artifacts, npm audit clean, all
  lockfile URLs point to registry.npmjs.org) · ignore-scripts=true is safe here
  precisely because no dep in the tree runs lifecycle scripts; min-release-age=
  7 days rejects freshly hijacked releases but is silently ignored by npm 10.9.8
  (takes effect on a newer npm) · use npm ci (not npm install) in CI/clean
  installs so the lockfile is enforced · 2026-07-13

## 2026-07-09 — M8 START (PLAN) — intervention correction flow

- SCOPE: M1–M7 = the planned MVP (all done). The hackathon deadline was extended
  to 2026-07-20, so post-M7 work CONTINUES the same milestone numbering (M8+)
  rather than an unnumbered "improvements" backlog — the milestone log is the
  thesis' design chapter and the "each milestone works end-to-end before the
  next" rule is exactly what stops three half-features landing by the 20th. M8+
  is explicitly labelled the post-MVP hardening phase.
- WHY M8 FIRST (over the MAPA catalog / pagination / search): it closes hard
  rules 1/4/7 that are today HALF-implemented — LLM output is persisted with NO
  human review step (rule 4 trust boundary), interventions cannot be soft-deleted
  (rule 1), and there is no correction path (rule 7). Highest demo-safety, lowest
  risk. The MAPA catalog (makes the legal dose/PHI validation REAL instead of a
  seeded mock) is the M9 candidate if runway allows.

M8.1 — review-before-persist (split FLUJO A into preview + commit): DONE (backend)
- SPLIT RegistrationPipeline into preview(audio, advisor_id) -> PreviewResult
  (transcribe + extract, NO DB write) and commit(fields, …) (resolve + VALIDATE +
  build + PDF + save). NO new service — same FLUJO A, same ports; a separate
  service would duplicate the resolution logic. PreviewResult is a frozen
  dataclass IN the pipeline (a core method's return, mirror of WeatherData), not
  an HTTP shape.
- REMOVED the old register() one-shot: after the split nothing in production calls
  it (the PWA uses the two phases; Telegram is gone, removed d403e8e), so keeping
  it only for the tests would be dead code + false coverage. The pipeline tests now
  call commit()/preview() directly — the seams production actually uses.
- VALIDATE in commit (rule 4/5) on the fields the advisor EDITED — the review can
  introduce an illegal dose, so commit re-validates; preview alone never persists.
  Advisor-active check runs in BOTH (fail fast in preview; commit re-checks as a
  separate request + needs the advisor for the PDF).
- raw_transcription stores the ORIGINAL audio transcription, not the edited fields
  → the record keeps the "what was heard vs what the advisor confirmed" audit
  trail. transaction_id (rule 3) is client-generated at commit; preview is
  side-effect-free so it needs none.
- ENDPOINTS: POST /api/records/preview (multipart audio → {transcription, fields});
  POST /api/records BECOMES the commit. NO Pydantic wrapper request model (first
  instinct, DISCARDED): every existing write endpoint declares its fields directly
  as args — with Form(...) for flat payloads. commit carries ExtractedFields (a
  NESTED object form-encoding can't represent), so it uses Body(...) args directly
  instead (fields: ExtractedFields = Body(...), + transaction_id/device_timestamp/
  transcription). Same "fields as args" convention, JSON instead of Form because
  there's no file — preview owns the multipart upload. ExtractedFields reused as
  the body is not a layering leak: the hand-edited fields are still untrusted input
  and ExtractedFields is exactly their rule-4 gate. So the M5 "introduce request
  models in a dedicated module" note does NOT trigger — Body(...) keeps zero new
  classes/modules.
- Initially DISCARDED any dry-run inside preview, then PARTIALLY REVERSED (user
  request, same session): preview now RESOLVES identities so the form shows real
  catalog names, but LEGAL validation (dose/area) still stays in commit — see the
  M8.1b note below. The split: name resolution is worth the 3 DB reads (the form
  showing raw "amavectina" is bad UX); dose/area caps still 422 on commit and the
  advisor re-edits.

M8.1b — resolve identities IN preview so the form shows catalog names (M8.3 UX):
- preview now fuzzy-resolves plot/product/equipment (the same repo lookups commit
  does) and CANONICALIZES the fields ("amavectina" -> "Abamectina", "Finca de PP"
  -> "Finca de Pepe"), so the advisor reviews real catalog names, not the raw
  mis-heard ASR text. Unmatched values are left as-is to fix.
- EXTRACTED a shared RegistrationPipeline._resolve(fields, advisor_id) used by BOTH
  preview (best-effort, no raise — canonicalize + flag) and commit (raises
  PlotNotFound/Product/Equipment on a missing mandatory). One source of truth; the
  error PRECEDENCE in commit is unchanged (plot -> missing-field -> product ->
  equipment). commit still re-resolves (defense in depth, rule 4): a hand-edited
  value that no longer matches 422s.
- PreviewResult carries the resolved entities; presenters.preview_result adds a
  per-identity resolution marker to the response ({plot:{found,crop,sigpac},
  product:{found}, equipment:{found}}). The form (ReviewForm) shows ✓ + the plot's
  crop/SIGPAC on a match, or a ⚠️ fix-it hint on a miss — but only while the field
  is UNTOUCHED, since the marker reflects the preview snapshot; once edited, commit
  is the authority. EXTRACTED presenters._sigpac (was inline in intervention_detail).

M8.2 — soft-delete + correction (rule 1 + rule 7):
- ADD Repository.soft_delete_intervention(id, advisor_id): UPDATE deleted_at=now()
  WHERE id AND advisor_id AND deleted_at IS NULL (scope = authorization). Endpoint
  DELETE /api/interventions/{id}: load live → 404 if foreign/unknown/already-gone,
  else soft-delete.
- ADD a small CorrectionService.supersede(id, advisor_id, new_fields,
  transaction_id): commit the NEW record first (idempotent via the client
  transaction_id) THEN soft-delete the old → a retry returns the existing new row
  and re-deleting the old is a no-op. Carries the old record's device_timestamp
  (rule 2: the treatment date does not change) + raw_transcription (audit chain).
  REUSES pipeline.commit; the service owns zero creation logic, only the
  soft-delete+commit orchestration (encodes rule 7). Endpoint POST
  /api/interventions/{id}/correction (JSON: edited fields + transaction_id).
- IN-PLACE update_intervention stays for FORWARD transitions only (execution,
  assessment); a correction never mutates a legal row in place.
- KNOWN gap: soft-deleting an EXECUTED record already counted by a signed campaign
  validation is allowed and not reconciled — acceptable for MVP, revisit if it bites.

M8.3 — PWA create flow: DONE, verified on a real phone. Recorder is now
two-phase — record → "Transcribir y revisar" (previewRecord, no save) → ReviewForm
→ "Confirmar y guardar" (commitRecord). api.js: createRecord SPLIT into
previewRecord (multipart) + commitRecord (JSON, Content-Type set by hand since it
is not FormData). transaction_id/device_timestamp still captured at record-stop and
reused on commit retry (rules 2/3); preview is side-effect free so retrying it is
free.
- ReviewForm prefills from the extracted fields; the record_type is an editable
  segmented control (the advisor can fix a mis-classification) and the fields shown
  switch on it (observation vs product/dose/pest/equipment + area/justification).
  buildPayload spreads the ORIGINAL fields first, so values the LLM extracted but
  the form doesn't render (operator_*, previous_alternatives, planned_date) still
  reach commit — no data loss. Numbers coerced, blank optionals -> null.
- Client stays thin: NO field validation beyond what the form types give; a
  missing/illegal value is the backend's 422, surfaced verbatim in the form so the
  advisor fixes it and resubmits (matches the "commit 422s, advisor re-edits"
  decision above). The transcription is shown read-only as "lo que dictaste".
- The detail-screen "corregir" (supersede) + "eliminar" (soft-delete) actions are
  NOT here — they depend on the M8.2 backend (soft_delete + CorrectionService), so
  they land with M8.2.

Tests: preview returns fields without persisting · commit re-validates edited
fields (illegal dose still 422) · soft-delete then read → 404 · supersede deletes
old + creates new + is idempotent on retry.

## 2026-07-08 — Temporary hackathon self-signup + Turnstile captcha

- Temporary hackathon self-signup (behind flags, OFF by default) · the permanent
  design is admin-only alta of advisors (no self-signup), but a hackathon judge
  needs to try the voice flow without the admin creating an account first ·
  enabled by `settings.hackathon_signup_enabled` (backend) + `VITE_HACKATHON_SIGNUP`
  (PWA) · the PWA shows a "Crear cuenta" path reusing the OTP flow with
  `shouldCreateUser: true`; on first login the user has a valid token but NO
  advisor row, so `POST /api/bootstrap` (new `current_auth_user` dependency that
  verifies the token WITHOUT requiring an advisor — `current_advisor_id` would
  401) provisions an ACTIVE demo advisor + a seeded sandbox (holding + 2 plots +
  "tractor") via `OnboardingService`, idempotent, matching the spec's canonical
  demo audio ("Finca de Pepe", araña roja on citrus) so recording works out of
  the box · products (Abamectina) are the shared MAPA catalog, not seeded · the
  only genuinely UNIQUE column that could collide across judges is `advisors.dni`
  (verified in the migrations), so demo ids carry an 8-hex slice of the auth uid ·
  App.jsx gates Home behind the bootstrap (sessionStorage `pending_bootstrap`
  flag) so the first list call never 401s on a missing advisor · to remove after
  the event: delete the flag, `/api/bootstrap`, `OnboardingService`,
  `current_auth_user`/`AuthUser`, the four `save_*` ports (optional, generic) and
  the PWA signup path · 2026-07-08
- Signup captcha deferred, not built · with self-signup the open OTP endpoint is a
  real abuse surface (bots, email-bomb, cost), unlike the closed login where a
  captcha added only friction · chosen: Supabase-native Cloudflare Turnstile
  (config toggle + token on the signInWithOtp call), not a custom captcha · left
  wired but inert (`getCaptchaToken()` returns undefined until `VITE_TURNSTILE_SITE_KEY`
  is set and the widget mounted) so it activates with no code change · Supabase's
  built-in rate limiting is the first line meanwhile · 2026-07-08
- Turnstile captcha implemented (was deferred) · Cloudflare Turnstile widget
  rendered on the whole login screen, not just signup, because Supabase's captcha
  protection is PROJECT-WIDE: once enabled it gates every credential endpoint
  (signInWithOtp for code + signup, signInWithPassword), so the token must ride on
  all three; verifyOtp is not gated and carries none · script loaded lazily from
  the login screen (explicit-render mode) so a normal visit never contacts
  Cloudflare · single widget instance, hidden (not unmounted) on the code-verify
  step to stay stable; token is single-use so we reset() after each credential
  call · fully inert until VITE_TURNSTILE_SITE_KEY is set AND Turnstile is enabled
  in Supabase Auth (with the secret key) — both flip together or login breaks ·
  no CSP change needed: verified the repo enforces none (the decisions note about
  "the PWA's CSP" was CSP-readiness / a deploy-layer policy, not in the code) · if
  a deploy-layer CSP exists, allow challenges.cloudflare.com in script-src +
  frame-src · 2026-07-08

## 2026-07-07 — Logging + per-stage timing instrumentation

- Logging turned on at INFO via a single `basicConfig` in the entry-point module
  (`api.py`, imported by uvicorn) · chosen over uvicorn's `--log-level` (only
  configures uvicorn's own loggers, not our `app.*`) and over a per-service setup
  (must run once, at the process entry point) · httpx/httpcore raised to WARNING
  to hide the Supabase client's per-request "HTTP Request:" INFO noise · 2026-07-07
- Added per-stage timing logs (helper `services/timing.py`: a `timed("label")`
  context manager logging elapsed ms at INFO) after a "runs a bit slow" report ·
  instruments the I/O hot spots (both Qwen calls, PDF render, OSS upload, AEMET)
  plus a per-flow total; totals wrap a thin `register`/`confirm` over an inner
  `_register`/`_confirm` so the existing body is not re-indented · measured a
  registration at ~5.5 s = Qwen audio 2.7 s + Qwen extract 1.4 s (~73%) + OSS
  0.5 s + Supabase ~0.9 s (7 sequential REST calls) + PDF 28 ms: the LLM
  round-trips dominate and are inherent, so no optimization pursued · 2026-07-07

## 2026-07-06 — History date filter (timezone-correct) + PWA visual refresh

- Extended `list_interventions` with optional `since`/`until` (UTC instants)
  instead of reusing `list_interventions_in_period` · the period method is
  holding-scoped, ascending and unbounded (it counts a holding's records for a
  campaign validation); the history/today list is advisor-scoped, newest-first
  and limited — the same query as Home, just date-bounded · discarded a third
  `list_advisor_interventions_in_period` (real duplication) and re-scoping the
  period method (breaks validations) · 2026-07-06
- `/api/interventions?from=&to=` are civil Madrid days; the inbound layer maps
  them to the exact UTC window `[from 00:00, (to+1) 00:00)` via `zoneinfo` before
  the DB filter · keeps the repo a plain `created_at` range AND stays DST-correct
  (rule 9) · discarded the frontend sending UTC instants (more client timezone
  juggling) and a naive civil-date comparison (the day-boundary fuzz the count
  method tolerates would drop a 00:30-Madrid record from "today") · 2026-07-06
- Today's list queries the backend by date (`from==to==` Madrid today) instead
  of fetching everything and filtering client-side · one code path for today and
  history, and the correct-timezone window is computed server-side once · list
  limit raised 100→500 so a season's history is not silently truncated (paginate
  if that ever breaks) · 2026-07-06
- PWA visual refresh keeps and refines the brand "cultivated soil" palette rather
  than going neutral-SaaS · the warm agronomic identity (from the prototype) sets
  it apart and is part of the TFG; emoji replaced by an inline SVG icon set (the
  PWA's CSP blocks icon fonts/CDNs), a shared AppBar and tinted status badges ·
  2026-07-06
- Dictation extracted to a reusable `<Dictate>` button (mic → POST /api/transcribe
  → text via callback) · the effectiveness assessment already had it and the
  campaign-validation remarks needed the same, so one component serves both
  instead of duplicating the MediaRecorder state machine · 2026-07-06

## 2026-07-04 — M7.3 PWA: validation screen (grouped by holding → campaign)

- ADDED Validation.jsx (route /validaciones, linked from Home): the advisor's
  holdings, each with its plots and, per campaign, the two conformity slots
  (Intermedia / Final) with a 0/2..2/2 counter. A signed slot shows the verdict
  + date + intervention count + a downloadable PDF (ValidationPdf mirrors
  PdfButton's blob-download); a missing slot offers a sign form (Conforme / No
  conforme + remarks; the backend requires remarks when not conform).
- The CURRENT campaign (device year, Europe/Madrid) is ALWAYS shown even with 0
  validations, so there is always somewhere to sign this year — computed
  client-side (campaigns = {current} ∪ {campaigns with validations}); no
  campaign is created in the DB until a validation row is inserted. Past
  campaigns appear only if they have validations.
- validation_date is the device clock at signing (hard rule 2). On success the
  screen re-fetches so the new validation + counter update.
- api.js: listHoldings, createValidation, getValidationPdfUrl.
- Pending: eyeball on a real phone + UI polish (next session) before marking M7
  done in the README.

## 2026-07-04 — M7.3 backend: holdings overview + validation PDF link

- ADDED GET /api/holdings: the advisor's holdings, each with its plots and ALL
  its validations, for the PWA validation screen. GROUPED BY HOLDING, not by
  plot — the prototype nests campaigns under a "parcela", but a validation is
  the HOLDING's (rule 6: records belong to the holding; Validation.holding_id +
  UNIQUE(holding, campaign, type)). Listing per plot would duplicate the same
  validation under every plot of a multi-plot holding and mislead the advisor.
  Each holding shows its plots so it stays recognisable (user's request).
- The PWA groups the validations by campaign and derives the 0/2 counter
  CLIENT-SIDE, so the server needs no "current campaign" concept. Made
  list_validations' campaign param optional (None -> all campaigns) to serve
  both the duplicate-check (one campaign) and this screen (all).
- One follow-up read per holding (plots + validations); an advisor has few
  holdings, same reasoning that keeps the intervention list lean.
- ADDED GET /api/validations/{id}/pdf: signs the signed-PDF link on demand
  (list carries has_pdf), scoped to the advisor via a new get_validation — a
  foreign id or a validation saved without a key (best-effort) is a 404. Mirrors
  get_intervention_pdf. New repo methods: list_holdings, list_plots,
  get_validation.

## 2026-07-03 — M7.2 backend: signed validation PDF (FLUJO C, Phase 5)

- ADDED generate_validation to the PdfGenerator port + ReportLab adapter: a
  Spanish conformity document (asesor · explotación · campaña/periodo/nº
  intervenciones/CONFORME-NO CONFORME/observaciones · firma), reusing the
  prescription's _section/_v/_fmt_* helpers. Content is the SUMMARY the row
  already holds — no per-intervention table (the simple thing that works; a
  table can come later if a validation ever needs to itemise the actuaciones).
- ADDED type-label + conformity mapping to Spanish in the adapter (MID_CYCLE ->
  "Intermedia", FINAL -> "Final de campaña"; True -> CONFORME). The enum stays
  English in code; the legal PDF is Spanish.
- CampaignValidationService now renders + uploads the PDF and sets
  validation_pdf_key on the SINGLE insert. Key is deterministic and known
  pre-save: validations/{holding}_{campaign}_{type}.pdf — unique because the DB
  enforces UNIQUE(holding, campaign, type). This avoids the save-then-update the
  prescription needs (its key uses transaction_id; a validation has none, and
  the row id is DB-generated / not serialized on insert).
- BEST-EFFORT like the prescription PDF (hard rule 8 spirit): a render/OSS
  failure logs + saves the validation without a key (the PDF is deterministic,
  regenerable from the row) — never blocks the signing. The advisor being
  absent (should not happen; they're authenticated) also just skips the PDF.
- The create response signs the link best-effort via a new _validation_response
  in api.py (mirrors _record_response — it does I/O, so it stays out of the pure
  presenters). The standalone GET /pdf endpoint is deferred to M7.3 (the PWA
  list will need it for pre-existing validations; nothing consumes it yet).
- Coverage: the service tests use a FakePdf, so ADDED a ReportLab smoke test
  (renders %PDF, tolerates remarks=None) — otherwise the real render had zero
  automated coverage — plus a manual generate_sample_validation.py to eyeball it.

## 2026-07-03 — Refactor: split JSON presenters out of api.py

- api.py had grown to 630 lines. MOVED the pure JSON-shaping helpers
  (record_fields, intervention_detail, validation_fields + _iso) to a new
  app/adapters/inbound/presenters.py — api.py drops to ~475 and now reads as
  routing + error mapping; presenters.py = how entities serialize (no FastAPI,
  no I/O, trivially testable). _record_response stays in api.py because it does
  I/O (signs a PDF link) and needs the container — the one presenter that isn't
  pure. NOT abstraction-ahead-of-need: it reorganises code that already existed.
  The endpoint tests already cover the presenters, so no new test file.
- ALSO sectioned api.py with banner comments (exception handlers · health · PWA
  REST API · legacy Telegram) and moved the whole Telegram path (webhook + its
  helpers + _TELEGRAM_NS) to the bottom, so the live PWA routes read together
  and the M1 legacy is visibly cordoned off. Reorder + comments only, no bodies
  touched; module docstring updated (PWA is the live inbound, Telegram legacy).

## 2026-07-03 — M7.1 backend: campaign validation (FLUJO C, Phase 5)

- ADDED the advisor's signed campaign validation via a new
  CampaignValidationService (POST /api/holdings/:id/validations): checks the
  holding is the advisor's (foreign/unknown -> indistinguishable 404), rejects a
  duplicate type, derives the covered period, counts its interventions, and
  saves. `ValidationType` modelled as a StrEnum (MID_CYCLE/FINAL) so a bad value
  is a 422 at the boundary — never reaching the DB CHECK / UNIQUE.
- NO campaigns table: a campaign stays a plain string label ('2026') on the
  validation row (UNIQUE holding+campaign+type). Considered a `campaigns` table
  grouping its two validations; DISCARDED — YAGNI: nothing needs a campaign
  entity of its own, the UI grouping is presentation (GROUP BY campaign), and a
  table would add a join + lifecycle for zero domain gain. Revisit if campaigns
  ever grow attributes (dates, crop calendar).
- PERIOD covered is AUTO-derived, not asked: the FIRST validation of a campaign
  starts at `campaign_start` (Jan 1 of the 4-digit year; ValueError ->
  InvalidCampaignError 422 so a malformed label fails loudly), later ones the
  day AFTER the previous `period_end` (no gap/overlap); end = signing date.
  Filtered by `created_at` (civil day, [start 00:00, end+1day)) — the one date
  every intervention carries (OBSERVATIONs have no device timestamp).
- A non-conform validation MUST carry remarks (else RemarksRequiredError 422);
  blank/whitespace remarks normalise to NULL, mirroring the assessment notes.
- SERVICE named `campaign_validation_service.py` / `CampaignValidationService`,
  NOT the spec's `validation_service.py` — that name is already the pipeline's
  LEGAL validation (dose/area). Deliberate deviation to avoid the collision;
  considered renaming the legal one (DISCARDED — churns existing imports for no
  gain).

## 2026-07-02 — M6 PWA: effectiveness assessment UI + mic dictation

- ADDED an AssessEffectiveness block on the detail of an EXECUTED record: three
  rating buttons (Buena/Regular/Mala -> GOOD/FAIR/POOR), an editable date
  (today by default), and an OPTIONAL reason. On save it PATCHes and the detail
  RE-FETCHES (reloadKey), same pattern as the execution confirm — the assess
  response is the lean list projection, so re-loading keeps the rich context.
- The reason is DICTATED: a mic button records (mirrors Recorder — getUserMedia
  + MediaRecorder), POST /api/transcribe turns it into text, and it lands in an
  EDITABLE textarea the advisor reviews/corrects before saving. Multiple
  dictations append. Chose transcribe-then-edit over transcribe-on-submit so
  nothing reaches the legal record unseen.
- ASSESSED detail now renders the full execution block PLUS a read-only
  "Valoración del resultado" (effectiveness chip + date + reason). The execution
  Section shows for EXECUTED *and* ASSESSED (an assessed record was executed
  first and keeps all applied data).
- ADDED the delivery-note number input to the execution confirm form (backend
  already accepted it; it belongs to EXECUTION, not the assessment).

## 2026-07-02 — M6 backend: effectiveness assessment (FLUJO C, Phase 4)

- ADDED EXECUTED -> ASSESSED via a new AssessmentService (mirrors
  ExecutionService): validates the state transition, stores effectiveness +
  date + reason, persists. Effectiveness modelled as an `Effectiveness` StrEnum
  (GOOD/FAIR/POOR, UI Buena/Regular/Mala) so PATCH /api/interventions/:id/
  effectiveness rejects a bad value at the boundary (422) like the list's
  `state` filter — never reaching the DB CHECK.
- ADDED two columns (migration): `effectiveness_date` (WHEN assessed) and
  `effectiveness_notes` (WHY, dictated). NOTE: neither is in the official Anexo
  III checklist — accepted as GIP good-practice/UX fields at the user's request
  (deliberate exception to "no speculative DB fields"). Blank notes normalise to
  NULL, not "".
- VOICE dictation split into its own POST /api/transcribe (speech->text ONLY,
  no extraction, no persistence): the PWA transcribes the reason, shows it in an
  EDITABLE textarea, then submits the reviewed text with the assessment. Chosen
  over transcribing inside the PATCH so the advisor sees/corrects what Qwen
  heard before it lands in the legal record; keeps AssessmentService pure (no
  audio I/O) and reuses the existing Transcriber port.
- The delivery-note number is NOT part of the assessment: it is captured at
  EXECUTION (already backend-wired) — the assessment is only effectiveness.
- Extended tests/test_serialize_columns to read `ALTER TABLE ... ADD COLUMN`,
  not just CREATE TABLE, so later column-adding migrations stay covered.
- PWA (assessment block + mic button) deferred to its own slice — kept this one
  backend-only to stop the milestone sprawling.

## 2026-06-30 — PWA: actions moved from the list row onto the detail

- MOVED PdfButton + ConfirmExecution out of TodayList into a shared
  RecordActions.jsx, rendered only on the detail screen. The list row is now a
  pure summary and the WHOLE <li> is the tap target (no inner buttons to avoid
  anymore), completing the prototype's "compact list -> rich detail" pattern.
- On a successful execution confirm the detail RE-FETCHES itself (reloadKey bump)
  instead of swapping in the confirm response: that response is the lean list
  projection, so re-loading keeps the rich context blocks (plot/holding/
  transcription) the detail renders. The list used to swap the row in place, but
  the list no longer shows actions, so a today-list refresh happens on next
  visit; acceptable (no live row to keep in sync).
- Added the spray volume / operator / operator-ROPO inputs to the confirm form
  (backend already accepted them), so the "Caldo"/"Aplicador" lines on the detail
  stop being permanently blank. Delivery-note number stays out — it is M6.

## 2026-06-30 — PWA: router + record detail screen (bridge M5→M6)

- ADDED React Router (was ad-hoc useState screen switching, fine for 2 screens,
  doesn't scale). HashRouter, NOT BrowserRouter: the PWA is served as static
  files with no SPA fallback, so reloading a deep link /registro/:id would 404;
  the hash keeps routing client-side. Switch to BrowserRouter once the host
  rewrites unknown paths to index.html. Routes: "/" Home, "/registro/:id"
  Detail, "/ajustes" Settings. Home is unchanged (record button + today list);
  tapping a list row's summary navigates to the detail (the PDF / confirm
  buttons stay outside the tappable region so they don't navigate).
- ADDED GET /api/interventions/:id with a RICH projection (the list fields plus
  prescription/execution detail + raw_transcription) AND plot/holding/equipment
  context (crop, variety, area, SIGPAC, owner, ROMA). Three extra reads per
  record, which is why the LIST stays lean and does not do them per row. Chose a
  dedicated endpoint over reusing the list payload (too thin for a real detail
  screen) — see the AskUserQuestion previews.
- EXPOSED raw_transcription ("lo que dictaste") only on the detail, not the list.
  The original AUDIO is still NOT shown: audio_storage_key exists on the model
  but the pipeline never uploads the audio — deferred to its own slice.
- Detail screen is READ-ONLY this slice: the PDF download and "confirmar
  ejecución" actions stay in the list for now; moving them onto the detail (as
  in the prototype) is the next slice. Lifecycle-state ICONS now live on the
  detail hero, so the earlier step-4b "icons in the list" item is effectively
  superseded by the list→detail split.

## 2026-06-30 — Plot alias uniqueness left to the admin (known gap)

- SAME collision class as the equipment alias bug, but NOT fixable the same way:
  the plot is the FIRST thing resolved from the audio, so there is no parent
  context to scope its lookup by (it is the plot that determines the holding).
  Two plots with the same alias across an advisor's holdings is therefore
  genuinely ambiguous by voice (the advisor dictates only the alias), so the
  only lever is uniqueness PER ADVISOR — which is already a documented design
  assumption, but the DB does not enforce it.
- DISCARDED enforcing it now: `plots` has no advisor_id column (it hangs off the
  holding), so a per-advisor unique rule needs a trigger or a denormalized
  advisor_id — more machinery than warranted while a SINGLE admin creates plots
  by hand (alta manual). KEPT as admin discipline + a detection query the admin
  can run periodically to catch duplicates before they bite:
    SELECT h.advisor_id, lower(p.voice_alias) AS alias, count(*)
    FROM plots p JOIN holdings h ON h.id = p.holding_id
    WHERE p.deleted_at IS NULL
    GROUP BY h.advisor_id, lower(p.voice_alias) HAVING count(*) > 1;
  REVISIT if there are ever multiple admins or automated plot creation.

## 2026-06-30 — Equipment alias resolved per holding, not per advisor

- BUG found: an advisor with two holdings, each owning a "tractor", got "no
  encuentro el equipo «tractor»" — the voice lookup scoped equipment to the
  ADVISOR (all holdings, JOIN holdings ON advisor_id), so the two identical
  aliases tied and best_match refused to guess (ambiguity guard). FIXED by
  scoping the lookup to the HOLDING already resolved from the dictated plot
  (the plot is resolved one step earlier and carries holding_id), so the two
  tractors never get compared. Drops the holdings JOIN -> a direct
  `.eq("holding_id", ...)`, which also closes the earlier gap where the lookup
  did not filter `holdings.deleted_at`.
- DISCARDED a per-advisor UNIQUE on the alias (forbid two "tractor" anywhere):
  it bans a legitimate, common case (a contractor advisor with N farms, each
  with "its tractor") and equipment has no advisor_id column (would need a
  trigger). Instead the alias is unique PER HOLDING via a partial unique index
  `(holding_id, lower(equipment_alias)) WHERE deleted_at IS NULL` (migration
  20260630120000) — lower() matches the fuzzy normalize, the WHERE respects
  soft-delete (rule 1). So: same alias across holdings = allowed and resolved;
  same alias within one holding = impossible by construction (the only truly
  ambiguous case). Plot aliases stay unique per advisor (resolved first, no
  parent context to scope by).
- test_serialize_columns now concatenates ALL migration files (was reading just
  the first via next(glob), which broke once a second migration existed).

## 2026-06-30 — M5 step 4a: iteaf_warning on execution

- DECIDED the ITEAF inspection validity = 3 years, in `settings`
  (`iteaf_validity_years`), not hard-coded in the domain · RD 1702/2011 set it
  at 5 years originally and 3 years for equipment in professional use since
  2020-01-01; a settings value documents it as a normative parameter that can
  shift again without touching domain code. DISCARDED 5 years (pre-2020, no
  longer current) and a fixed domain constant (would bury a legal number in a
  pure function). The value is injected into `ExecutionService` via the
  container, so the service stays free of a `settings` import (hexagonal).
- ADDED pure `iteaf_inspection_expired(treatment_date, inspection_date,
  validity_years)` in `calculations.py` — the slot its docstring had reserved.
  A MISSING inspection date counts as a warning (True): an unrecorded inspection
  cannot prove the machine is in-date. Leap-day guard (Feb 29 -> Feb 28 in a
  non-leap expiry year).
- ADDED `Repository.get_equipment(equipment_id)` (only `get_equipment_by_alias`
  existed) · FLUJO B needs to load the machine by id to read its inspection date.
  `ExecutionService` sets `iteaf_warning` only when an equipment is linked (an
  OBSERVATION has none); it is a NON-BLOCKING notice, never a block (rule 8
  spirit). No DB migration: both columns already existed in the initial schema.

## 2026-06-29 — Architecture: functional core for single-concept domain rules

- KEPT the anemic-dataclass + transaction-script-service style on purpose · the
  real invariants here are cross-entity (dose ≤ product.max_allowed_dose, area ≤
  plot.enclosure_area_ha), so they live naturally in services, not on one
  entity. Fowler's anemic-model critique targets large OO systems; for a small,
  solo TFG domain a transaction script is the "code you fully understand" choice
  (CLAUDE.md). NOT migrating to rich aggregates · 2026-06-29
- ADDED `states.transition(intervention, new)` as the SINGLE gate for state
  changes (validate_transition then mutate) · stops any service from leaving an
  intervention in an illegal state by assigning `lifecycle_state` directly. Type
  hint imported under TYPE_CHECKING to avoid the models↔states circular import ·
  2026-06-29
- ADDED `core/domain/calculations.py` for pure single-concept domain rules and
  moved `earliest_harvest_date` there (was inline in registration_pipeline) · the
  M5 execution service will compute the same value, so a shared pure function is
  one source of truth instead of a copy-paste. Rule of thumb logged for the
  thesis: data in dataclasses · single-concept rules in domain functions
  (states.py, calculations.py) · cross-entity rules + orchestration + I/O in
  services. DISCARDED adding the ITEAF-expiry check now — it needs the inspection
  validity period decided first, so it waits for M5 (no speculative code) ·
  2026-06-29

## 2026-06-29 — M5 progress checkpoint (resume here)

- DONE · step 1: FLUJO B backend (execution confirmation, PRESCRIBED -> EXECUTED)
  end-to-end at the API level, with tests. Commits dd2c21d (calculations + state
  gate) and 06082b5 (FLUJO B). Weather NOT captured yet.
- DONE · step 2: PWA "✅ Confirmar ejecución" button on PRESCRIBED records,
  verified on a real phone (see entry below).
- DONE · step 3: weather via Open-Meteo, captured inside FLUJO B (see entry below).
- DONE · step 4a: `iteaf_warning` computed on execution AND surfaced in the PWA
  list ("⚠️ Inspección ITEAF caducada"); exposed via the API projection.
- TODO · step 4b: lifecycle-state icons in the PWA list — DEFERRED. It is
  cosmetic (the state already shows as a coloured badge). Folded into the
  planned PWA refactor below instead of done piecemeal now.
- NEXT (between M5 and M6, NOT inside M5): PWA refactor toward the prototype
  (`docs/agrovoz_prototipo.html`) — introduce React Router (today navigation is
  ad-hoc `useState` in App.jsx, fine for 2 screens, doesn't scale to Home +
  Historial + detail) and a list->detail pattern so the execution data (weather,
  earliest harvest, ITEAF) lives on a detail screen instead of fattening each
  list row. Incremental: Home + Historial + ONE detail screen, NOT the 11
  prototype screens. NEVER build screens without a backend (map, plot alta,
  campaign validation = M6/M7). The prototype is a visual MAP, not a contract —
  its Login still shows the dropped magic link.
- OPEN gap (unrelated): Supabase client has no explicit timeout (see note below).

## 2026-06-29 — M5 step 3: weather via Open-Meteo (FLUJO B)

- ADDED the `Weather` port (`core/ports/weather.py`) + `OpenMeteoWeather` adapter
  · one method `conditions_at(lat, lon, day)` returning the existing `WeatherData`.
  CHOSE Open-Meteo over AEMET · free, keyless, lat/lon direct; the *forecast*
  endpoint with explicit `start_date`/`end_date` also serves the recent past
  (~92 days), covering a deferred execution. AEMET stays pluggable behind the port
  (one line in container.py). DISCARDED the archive endpoint for older dates · out
  of MVP scope · 2026-06-29
- DECIDED to read the HOURLY 12:00 (local) sample as representative of the day ·
  the PWA captures only the application DATE, not the hour. Refinable later (real
  hour, or daily aggregates for drift) in the adapter alone · 2026-06-29
- KEPT `WeatherData` as the port's return shape while `Intervention` keeps the
  four weather columns FLAT · the entity mirrors the flat legal-record table, the
  value object is just transport; the service maps one onto the other, so the
  adapter never learns how the record is persisted (asked: "isn't this modeled
  weirdly / duplicated?" — answer: DTO-vs-entity overlap, on purpose) · 2026-06-29
- BOUNDARY rule: the adapter catches `Exception` and wraps EVERYTHING (timeout,
  HTTP status, malformed/missing JSON, unexpected shape) into `WeatherError`, so
  the service handles one thing and rule 8 (never block) always holds. Capture is
  best-effort in `ExecutionService._capture_weather`: no plot coordinates OR a
  `WeatherError` -> `audit_state='WEATHER_PENDING'`, fields left empty, record
  saved anyway; success -> 4 fields + `audit_state='VALID'`. Uses the plot
  centroid (PWA sends no device GPS yet, so gps_lat/lon stay None) · 2026-06-29
- 3 new tests (weather captured / provider failure defers / no-coords defers);
  full suite 61 passed · 2026-06-29
- SURFACED the weather: `_record_fields` (create + list responses) now also
  returns `temperature_c/relative_humidity_pct/wind_speed_kmh/wind_direction` +
  `audit_state` (additive, nothing else changes). The PWA list shows a compact
  line (🌡️ °C · 💧 % · 💨 km/h dir) that skips any empty reading, or "⛅ Clima
  pendiente" when `audit_state=WEATHER_PENDING`. Shows on EXECUTED rows; a
  prescription has no weather yet. Verified on a real phone · 2026-06-29

## 2026-06-29 — M5 step 2: PWA "Confirmar ejecución" button (FLUJO B)

- ADDED `confirmExecution(id, {...})` in `pwa/src/api.js` · `PATCH
  /api/interventions/:id/execution` with FormData (matches the backend `Form(...)`,
  like createRecord). Only `treatment_date` is required; dose/area sent only when
  typed (backend falls back to prescribed/holding values and re-validates).
- ADDED a `ConfirmExecution` component in `TodayList.jsx` shown only on PRESCRIBED
  rows · collapsed = a link, expanded = date (prefilled to today as the device
  sees it in Europe/Madrid, EDITABLE because the treatment may predate the
  confirmation — rule 2) + optional real dose + optional treated area (the two
  figures the backend re-validates). DECIDED date-only via `<input type=date>`
  sent as noon UTC · the picked calendar day then matches both in UTC
  (earliest_harvest = treatment_date.date()) and in Madrid, no midnight roll;
  legally the day is what matters (PHI in days, weather per day). On success the
  row is swapped in place for the returned EXECUTED record (no refetch).
- KNOWN limit: the Home list is today-only, so a deferred prescription from
  another day isn't visible to confirm there yet — a later view will cover it.
  Verified on a real phone · 2026-06-29

## 2026-06-29 — M5 step 1: FLUJO B backend (execution confirmation, no weather)

- ADDED `ExecutionService.confirm` (FLUJO B) mirroring `RegistrationPipeline`: a
  class with the Repository injected, wired in container.py · symmetry with FLUJO
  A · 2026-06-29
- State change goes through `states.transition` (the single gate): only
  PRESCRIBED -> EXECUTED. A double confirm fails there (EXECUTED -> EXECUTED is
  illegal), so NO idempotency key is needed for this endpoint · 2026-06-29
- Re-validate legality with the REAL dose/area at execution (hard rule 5): the
  prescription was validated at creation, but applied figures can differ. Reuses
  the extracted `validate_legality` (one source of truth) and needs two new repo
  getters: `get_plot(id)` and `get_product_by_registration_number` · 2026-06-29
- `treatment_date` is a SINGLE client-sent value, not a pair · the server cannot
  do a "device-clock" fallback without using its own clock (forbidden by hard
  rule 2); the PWA prefills the field with the device clock (editable for a
  treatment applied days earlier), so the date is never absent · DISCARDED
  passing device_timestamp + optional treatment_date · 2026-06-29
- DEFERRED letting a DIRECT execution (voice, FLUJO A) carry an explicit past
  date · it would need a new ExtractedFields date + prompt change (more scope,
  touches the LLM); the prescribe->confirm path already covers "applied earlier" ·
  2026-06-29
- Endpoint `PATCH /api/interventions/{id}/execution` uses `Form(...)` fields, NOT
  a Pydantic body model · consistency: create_record already uses Form and the
  PWA sends FormData; there are zero request models today, so adding one (and a
  DTO module for a single class) would be abstraction ahead of need. CRITERION
  for later: if endpoints grow rich/nested JSON bodies, introduce Pydantic models
  in a dedicated module and migrate all at once · 2026-06-29

## 2026-06-29 — Known gap: Supabase client has no explicit timeout (TODO)

- NOTED, not yet fixed · `get_client()` calls `create_async_client` with no
  `ClientOptions`, so DB queries inherit supabase-py's default
  `postgrest_client_timeout = 120s` (handed to the underlying httpx client; NOT
  httpx's own 5s). `_run` translates the eventual ReadTimeout to RepositoryError
  → 503, but only after ~120s. Qwen/OSS/Telegram are bounded at 30s
  (`vendor_timeout_seconds`); Supabase is the outlier and it sits on the
  synchronous PWA paths (`POST /api/records`, `PATCH .../execution`) where the
  advisor waits. FIX when convenient: pass
  `ClientOptions(postgrest_client_timeout=settings.vendor_timeout_seconds)` ·
  2026-06-29

## 2026-06-29 — M4: login by email OTP code + password (drop magic link)

- REPLACED the magic-link login with an email **OTP code** (6 digits) as the
  primary method · tapping a magic link from the iPhone mail app can open a
  different browser than the one holding the installed PWA, so the session lands
  in the wrong place and login appears to "do nothing". A code is read in the
  mail app and typed/pasted into whichever browser already has the PWA open —
  no cross-browser handoff · 2026-06-29
- Code request uses `signInWithOtp({ shouldCreateUser: false })` · only advisors
  already registered in Supabase may log in (the email must pre-exist); we never
  create accounts from the login screen · 2026-06-29
- Code is verified with `verifyOtp({ type: 'email' })` · same one-time token the
  Magic Link email template carries; requires that template to include
  `{{ .Token }}` in the Supabase dashboard (config step, not code) · 2026-06-29
- ADDED password as a secondary login method (`signInWithPassword`, the "user"
  is the email — no separate usernames) · field users who set a password skip
  waiting for a code each shift · 2026-06-29
- Password is set/changed from inside the app (Ajustes → `updateUser`), NOT via
  a reset-password email · the user is already authenticated there, so it is a
  single call · DISCARDED the `resetPasswordForEmail` + PASSWORD_RECOVERY flow:
  more screens and an extra round-trip for no gain once you can log in by code ·
  2026-06-29

## 2026-06-26 — Robustness pass: vendor timeouts, RepositoryError, idempotency race

- Synchronous vendor SDKs run in worker threads get an explicit 30s transport
  timeout (settings.vendor_timeout_seconds): DashScope `request_timeout` (default
  300s) and OSS `connect_timeout` (default 60s × 3 retries) · high defaults hang
  a field advisor AND leak the ThreadPoolExecutor until it saturates; the
  transport timeout kills the request so the thread dies and surfaces as a domain
  error · discarded `asyncio.wait_for` (returns control but leaves the thread
  orphaned, pool still fills up); Supabase left untouched (async client, no
  thread pool — different failure mode) · 2026-06-26
- Repository wraps PostgREST/network failures as RepositoryError (a new
  InfrastructureError subtype) via a single `_run()` helper around `.execute()` ·
  a DB outage is infrastructure (inbound → 503 "retry"), not the catch-all 500
  "bug"; deserialization stays OUTSIDE the wrap so a mapping bug remains a real
  500 · 2026-06-26
- save_intervention catches the UNIQUE(transaction_id) violation (SQLSTATE
  23505) and returns the already-saved row · closes the TOCTOU between the
  pipeline's idempotency pre-check and the INSERT: two concurrent same-tx
  requests both pass the check, the constraint rejects the loser, and we honour
  idempotency (hard rule 3) instead of returning a 503; any other unique
  violation finds no row and re-raises · 2026-06-26

## 2026-06-25 — M4: fix mobile PDF download (cross-origin attachment → blob)

- PWA now FETCHES the signed PDF into memory and serves it via a same-origin
  `blob:` URL (download attribute honoured), instead of linking the `<a>`
  straight at the cross-origin OSS URL · navigating to a cross-origin attachment
  silently does nothing on mobile (works on desktop): the `download` attribute is
  ignored cross-origin and the phone swallows the same-tab navigation with NO
  error — the classic "browser quietly refuses and never tells you". A
  same-origin blob URL is the one thing that downloads reliably on desktop AND
  mobile · 2026-06-25
- Force `https://` on OSS_ENDPOINT (in `.env` AND a normaliser in OssStorage) ·
  oss2 signs presigned URLs with the endpoint's scheme; an `http://` endpoint
  produced an http URL that the HTTPS PWA refused to fetch as MIXED CONTENT (a
  browser never lets an HTTPS page load an HTTP resource). The code normaliser is
  belt-and-suspenders so a misconfigured `http://` value can't reintroduce it ·
  2026-06-25
- Added a CORS rule (allowed origin, GET) on the OSS bucket · once the URL was
  HTTPS, OSS answered 200 but the browser blocked JS from READING the response
  (no Access-Control-Allow-Origin) — a `fetch()` to another domain needs that
  domain's explicit permission. Was a non-issue while we merely navigated to the
  URL; it appears precisely because we now fetch it · 2026-06-25
- KEPT the two-tap flow (prepare → download) · not a bug: the second tap is the
  native user gesture mobile needs to save a file (a programmatic click/location
  change after the await is outside the gesture and gets ignored). Robustness, on
  purpose — extends the 06-23 two-tap decision, now also covering the fetch step ·
  2026-06-25

## 2026-06-23 — M4 step 4: PWA wiring (auth + upload + today's list)

- Magic-link auth via the official @supabase/supabase-js SDK (not a hand-rolled
  fetch against /auth/v1/otp+verify) · the SDK handles the PKCE redirect, token
  storage and silent refresh — reimplementing that is more code and more fragile,
  against the "code you fully understand / simple thing that works" TFG rule ·
  2026-06-23
- Browser client uses the new PUBLISHABLE key (sb_publishable_…), not the legacy
  anon key · Supabase's current public client key; exposed as VITE_* (public by
  design — only grants what Auth+RLS allow). Secret key never reaches the bundle ·
  2026-06-23
- Dev cross-origin solved with a Vite proxy (/api → localhost:8000), NOT backend
  CORS · the browser then sees one origin, so zero CORS config and it works
  through the cloudflared tunnel (phone→tunnel→Vite→proxy→backend). Supabase Auth
  calls go direct (Supabase sends its own CORS). DISCARDED adding CORSMiddleware ·
  2026-06-23
- Expose created_at in the API record projection · the Home "today" filter needs
  one date present on EVERY row; prescription_date/treatment_date are null for
  OBSERVATIONs, created_at (DB-generated) is the only universal one. Not a new DB
  field — just lets an existing column out (resolves the 06-19 "deferred date
  filter") · 2026-06-23
- "Today" decided in Europe/Madrid via Intl.DateTimeFormat (not raw UTC date) ·
  CLAUDE.md rule 9 (UTC stored, local rendered); a record at 00:30 Madrid is
  today, not yesterday's UTC day · 2026-06-23
- transaction_id (crypto.randomUUID) + device_timestamp captured ONCE when the
  recording stops and reused on retry · hard rules 2+3: the device clock is the
  treatment date, and a stable idempotency key means a network-error retry hits
  the existing row instead of duplicating a legal record · 2026-06-23
- Recording auto-uploads on an explicit "Enviar" tap, not on stop · the POST is
  synchronous and slow (Qwen); the advisor reviews/replays the take first and a
  failed upload retries the SAME take · 2026-06-23
- TodayList fetches inline in the effect with an `active` guard + a refetch via
  refreshKey/attempt counters (not a useCallback) · react-hooks 7's
  set-state-in-effect rule can't see the await across a useCallback boundary;
  inline keeps every setState provably post-await · 2026-06-23
- PDF opened via a NEW endpoint GET /api/interventions/{id}/pdf that signs the
  OSS URL on demand, not a URL embedded per list row · realises the list's
  stated "sign on demand" design (one signing call only when tapped, not N per
  list); new repo method get_intervention(id, advisor_id) where the advisor
  scope IS the authorization (another advisor's id → indistinguishable 404) ·
  2026-06-23
- Record without a PDF (OBSERVATION, or failed render) → 404 PDF_NOT_FOUND, same
  as a missing record · there is no document to return; endpoint raises no
  domain errors, reusing the app-level handlers (repo crash → catch-all 500, OSS
  signing failure → InfrastructureError 503), consistent with the other routes ·
  2026-06-23
- PWA DOWNLOADS the signed PDF in TWO taps: tap 1 signs the URL (async), tap 2
  is a real <a> the user clicks · inline/new-tab lost to the browser's "download
  PDFs" setting and mobile blank tabs; and a programmatic click / location change
  AFTER the await is outside the user gesture, so mobile Chrome ignored it. A
  genuine tap on a ready same-tab <a> (OSS attachment → downloads in place) is the
  one thing that works on desktop AND mobile · 2026-06-23
- presigned_url signs response-content-disposition=attachment;filename · forces
  the download with a sensible name on every device. NOT response-content-type:
  the object already stores Content-Type application/pdf (set at upload) and OSS
  rejects overriding it ("can not override response header on content type") ·
  2026-06-23
- New Storage.exists (HEAD via oss2 object_exists), checked before signing the
  PDF link · a DB key can outlive its object (other bucket / deleted), and a
  signed URL to a missing object shows OSS's raw NoSuchKey XML in the browser;
  the HEAD turns it into a clean 404 PDF_NOT_FOUND · 2026-06-23

## 2026-06-22 — M4 step 1: installable PWA scaffold (Vite + React + Tailwind)

- Stack = Vite + React (JavaScript, not TypeScript) + Tailwind v4 + vite-plugin-pwa
  · React has the most AI/tutorial/StackOverflow support (decisive for a frontend
  beginner) and is the most defensible for a TFG; plain JS over TS to remove a
  layer of complexity (backend already gives type rigor via Pydantic) · 2026-06-22
- Tailwind ALONE, no Bootstrap (tutor suggested combining) · Tailwind already
  covers the responsive need Bootstrap is known for, via sm:/md:/lg: breakpoints;
  loading both = two competing CSS systems (conflicting resets, extra weight,
  harder to understand — against the "code you fully understand" TFG rule). Pick
  one · 2026-06-22
- DISCARDED packaging as a native app (tutor's "native PWA" = TWA/Capacitor for
  the Play Store) · the installable PWA already gives install + offline; store
  packaging is post-MVP and only if store distribution is needed · 2026-06-22
- Safe-area handling from the START (tutor's strongest point: device margins
  differ per phone) · viewport-fit=cover in index.html + env(safe-area-inset-*)
  exposed as reusable @utility classes (pt-safe/pb-safe/p-safe); every future
  screen opts in with one class. Two-layer layout (safe padding on outer,
  design padding on inner) so they don't override each other · 2026-06-22
- min-h-dvh over min-h-screen (100vh) · 100vh miscalculates on mobile (browser
  chrome shows/hides); dvh tracks the real visible height · 2026-06-22
- HTTPS on the phone via a cloudflared quick tunnel (not Vite basic-ssl, not the
  Chrome insecure-origin flag) · service worker AND getUserMedia need a secure
  context; the tunnel gives a real trusted cert (no warnings), works off-Wi-Fi,
  and unblocks both real WebAPK install and the M4-step-2 microphone. Over plain
  LAN HTTP Chrome only offered a shortcut, not a true install · 2026-06-22
- server.allowedHosts=true in vite.config · the tunnel forwards a *.trycloudflare.com
  Host that changes each run and Vite's DNS-rebinding guard would block it; safe
  as this is the dev server only · the tunnel is ephemeral (killed = private again) · 2026-06-22

## 2026-06-19 — CI green: lazy OSS bucket (surfaced by GitHub Actions)

- OssStorage builds its oss2.Bucket lazily (_get_bucket on first use), not in
  __init__ · the Bucket constructor validates the endpoint, so eager
  construction made merely IMPORTING the app require a live OSS config; an empty
  OSS_ENDPOINT (CI, no .env) crashed at collection. Now mirrors the Supabase
  adapter's lazy client; imports/tests that mock storage need no OSS config ·
  2026-06-19
- GitHub Actions: pytest on push/PR via uv (uv sync --frozen); only the 4
  no-default settings get dummy env values (telegram/supabase_url/
  supabase_service_key/dashscope) — unit tests use fakes, never real services ·
  2026-06-19

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
