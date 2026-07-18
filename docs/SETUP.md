# Setup — install & run from a clean machine

Two processes: the **backend** (FastAPI, port 8000) and the **PWA** (Vite,
port 5173). Phone testing adds a third: an HTTPS tunnel.

## Prerequisites

- **Python 3.12** and [`uv`](https://docs.astral.sh/uv/)
- **Node.js + npm** (for the PWA)
- **`cloudflared`** (only for testing on a real phone — mic and PWA install
  require HTTPS)
- Accounts / keys:
  - **Supabase** project (PostgreSQL + Auth) + the **Supabase CLI** to apply
    the schema (`supabase/migrations/`).
  - **DashScope** API key (Qwen3-ASR-Flash + Qwen-Flash)
  - **Alibaba Cloud OSS** bucket + access keys (audio and PDF storage)

> **Note on accounts:** there is no self-signup. The admin provisions each
> advisor (profile, holdings, plots with SIGPAC + voice alias, equipment,
> product catalog) directly in Supabase, and creates their auth user; the
> advisor then just logs in with an email OTP code. The onboarding steps and
> every user flow are described in [`USER_GUIDE.md`](USER_GUIDE.md).

## 1. Backend

```bash
uv sync                                       # install deps from pyproject/uv.lock
cp app/config/.env.example app/config/.env
```

Fill `app/config/.env` by hand: `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`,
`DASHSCOPE_API_KEY` and the `OSS_*` keys. **The `.env` is never committed.**

Apply the database schema (once per Supabase project):

```bash
supabase link --project-ref <your-project-ref>
supabase db push        # applies supabase/migrations/ in order
```

(Equivalent without the CLI: paste the files from `supabase/migrations/` into
the Supabase SQL Editor, in filename order.)

```bash
uv run uvicorn app.adapters.inbound.api:app --host 127.0.0.1 --port 8000 --reload
```

Quick check: `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`.

The backend has no UI of its own — the client is the PWA, which calls this
server over `/api/...`.

## 2. PWA

From the repo root:

```bash
cd pwa
npm install        # first time only
npm run dev        # Vite dev server on port 5173
```

## 3. HTTPS tunnel (phone testing)

The microphone and PWA installation require a secure origin, so testing on a
phone needs an HTTPS tunnel, not `http://localhost`:

```bash
cloudflared tunnel --url http://localhost:5173
```

Open the `https://…trycloudflare.com` URL it prints on the phone, sign in with
the code emailed to you (or with a password set in Ajustes), record a note and
it shows up in today's list.

## Safe shutdown

- **Backend** — stop Uvicorn with `Ctrl + C`.
- **PWA** — `Ctrl + C` in both terminals: the tunnel (`cloudflared`) first,
  then Vite. Closing the tunnel destroys the ephemeral `trycloudflare.com`
  URL, so there is nothing to revoke.

## Tests

Few tests by methodology (one test per edge case, no exhaustive suite):

```bash
uv run pytest                                  # whole suite
uv run pytest tests/test_registration_pipeline.py   # single file
```

| File | What it tests |
| --- | --- |
| `test_registration_pipeline.py` | FLUJO A end-to-end (with fake ports) |
| `test_execution_service.py` | FLUJO B: execution confirmation + weather + ITEAF warning |
| `test_assessment_service.py` | FLUJO C: effectiveness assessment (EXECUTED → ASSESSED) |
| `test_campaign_validation_service.py` | M7: campaign validation (period, conformity, remarks) |
| `test_correction_service.py` | M8.2: correction by supersede + soft-delete |
| `test_validation_service.py` | legal validation (dose, area, authorized product) |
| `test_reportlab_pdf.py` | PDF generation (prescription/validation documents) |
| `test_schemas.py` | `ExtractedFields` (sanitizing the LLM output) |
| `test_serialize_columns.py` | domain model ↔ DB columns (no drift) |
| `test_fuzzy_lookup.py` | fuzzy lookup of plot/product/equipment by alias |
| `test_states.py` | state-machine transitions |
| `test_auth.py` | Supabase JWT verification (`current_advisor_id`) |
| `test_api.py` | endpoints and error mapping to `{error, mensaje}` |

## Production deployment (Alibaba Cloud ECS)

The live instance is an Alibaba Cloud ECS **`ecs.e-c1m2.large`** in the
**Singapore** region, serving **https://agrovoz.pedrofloresnavarro.com**. The
repo is cloned at `/opt/agrovoz`; there is no Docker (single-user MVP, by
methodology).

- **Backend** — a systemd unit (`agrovoz.service`) runs
  `uv run uvicorn app.adapters.inbound.api:app --host 127.0.0.1 --port 8000`
  from `/opt/agrovoz`, with `Restart=always` (`RestartSec=3`) and enabled at
  boot (`systemctl enable --now agrovoz`). The backend only listens on
  localhost — nginx is the public face.
- **PWA** — built on the instance (Node 20 via NodeSource; `npm ci &&
  npm run build` in `pwa/`) and served by **nginx** as static files from
  `/opt/agrovoz/pwa/dist`, with the SPA fallback
  (`try_files $uri $uri/ /index.html`).
- **Reverse proxy** — the same nginx server block proxies `/api/` to
  `127.0.0.1:8000`, with `client_max_body_size 25M` (audio uploads) and
  `proxy_read_timeout 120s` (the Qwen round-trips). **HTTPS** via Let's
  Encrypt (`certbot` + `python3-certbot-nginx`) — the mic and the PWA
  install require a secure origin in production exactly as in development.
- **Configuration** — same two env files as development, living only on the
  instance with `chmod 600`, never in git: `app/config/.env` (Supabase,
  DashScope and OSS keys — the OSS bucket is reached from here) and
  `pwa/.env.local` (build-time PWA variables, baked in by `npm run build` —
  rebuild after changing it).
