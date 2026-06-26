# Asesor GIP — middleware de voz para registros fitosanitarios

El asesor dicta una nota de voz en campo (*"Finca de Pepe, Abamectina 1,5 litros
por hectárea, araña roja, tractor"*) y el sistema genera el registro fitosanitario
legalmente válido: transcripción (Qwen-Audio) → extracción de campos a JSON
(Qwen Instruct) → validación legal → Supabase (PostgreSQL) → PDF oficial.

Contexto legal: RD 1311/2012 (Anexo III) y Reglamento UE 2023/564. El registro
fitosanitario electrónico es obligatorio en España desde el 2027-01-01.

> Proyecto de TFG. La especificación completa está en `docs/mvp_asesor_gip_v3.md`.

## Estado actual

Se construye en hitos incrementales; cada uno funciona de punta a punta antes
de empezar el siguiente.

- [x] **M1** — Spike: audio → JSON por consola (validar que Qwen entiende a un
      asesor de campo). Desechable, archivado en `docs/historico/spike_main.py`.
- [x] **M2** — **Probado end-to-end.** Nota de voz de Telegram → transcripción +
      extracción con Qwen → validación legal → fila persistida en Supabase.
      Arquitectura hexagonal (núcleo + puertos + adaptadores), búsqueda difusa de
      parcela/producto/equipo por alias dictado.
- [x] **M3** — **Probado end-to-end.** PDF de prescripción (ReportLab) + subida a
      Alibaba Cloud OSS, con enlace firmado (caduca en 1h) descargado desde el móvil.
- [x] **M4** — **Probado en un móvil real.** PWA instalable (React + Vite +
      Tailwind): login por magic-link de Supabase, botón de grabación, subida del
      audio al mismo pipeline, lista de registros de hoy y descarga del PDF bajo
      demanda.
- [ ] M5 — máquina de estados + confirmación de ejecución + clima AEMET ·
      M6 — evaluación de eficacia + nº de albarán · M7 — validaciones de campaña.

## Stack

**Backend**: Python 3.12 · FastAPI + Uvicorn · Pydantic V2 · Supabase
(PostgreSQL + Auth magic-link) · Qwen-Audio + Qwen Instruct vía DashScope ·
Alibaba Cloud OSS · ReportLab. Dependencias con `uv`.

**PWA (M4)**: React 19 + Vite + Tailwind + vite-plugin-pwa. Dependencias con `npm`.

## Arquitectura (hexagonal, desde M2)

```
app/
  core/        domain/ (modelos, schemas, estados, errores)
               ports/  (ABCs: Transcriber, Extractor, Repository, Notifier,
                        Storage, PdfGenerator)
               services/ (registration_pipeline = FLUJO A)
  adapters/    inbound/  api.py (webhook FastAPI de Telegram)
               outbound/ qwen.py · supabase_repo.py · oss_storage.py ·
                         reportlab_pdf.py · telegram.py
  config/      settings.py · container.py (composition root) · .env
pwa/           React + Vite + Tailwind + vite-plugin-pwa (cliente M4)
```

El núcleo solo depende de puertos (ABCs): el webhook de Telegram y la PWA llaman
al **mismo** pipeline (`POST /api/records`) sin tocar lógica de negocio.

## Instalación y ejecución local

**1. Instalar dependencias**
```bash
uv sync
```

**2. Configurar las claves**
```bash
cp app/config/.env.example app/config/.env
# Rellena a mano: TELEGRAM_TOKEN, SUPABASE_URL/SERVICE_KEY, DASHSCOPE_API_KEY,
# OSS_* y DEFAULT_ADVISOR_ID (el UUID de un asesor ACTIVE que tengas sembrado
# en Supabase). Nunca se commitea el .env.
```

**3. Levantar el servidor** (puerto 8000, recarga automática)
```bash
uv run uvicorn app.adapters.inbound.api:app --host 127.0.0.1 --port 8000 --reload
```
Comprobación rápida: `curl http://127.0.0.1:8000/health` → `{"status":"ok"}`.

**4. Exponer el servidor a internet** (en otra terminal)
```bash
ngrok http 8000
```
*(Copia la URL pública `https://…` que genera.)*

**5. Conectar el webhook de Telegram**
```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://<URL_DE_NGROK>/telegram/webhook"}'
```

Listo: envía una **nota de voz** al bot y responderá con el registro persistido.

> **Telegram es el stand-in de M2 y solo hace una cosa: registrar una
> intervención** (audio → registro persistido + PDF). No tiene autenticación por
> asesor, ni lista de registros, ni descarga de PDF bajo demanda — todo eso vive
> **solo en la PWA** (M4). Telegram se mantiene como vía rápida de prueba del
> pipeline; el cliente real es la PWA.

## PWA (M4)

El cliente que usan los asesores. Necesita el backend levantado (sección
anterior, puerto 8000). Desde la raíz del repo:

**1. Instalar dependencias** (solo la primera vez)
```bash
cd pwa
npm install
```

**2. Arrancar el servidor de desarrollo** (Vite, puerto 5173)
```bash
npm run dev
```

**3. Exponerla por HTTPS** (en otra terminal) — el micrófono y la instalación
de la PWA exigen un origen seguro, así que para probar en el móvil hace falta un
túnel HTTPS, no `http://localhost`:
```bash
cloudflared tunnel --url http://localhost:5173
```
Abre en el móvil la URL `https://…trycloudflare.com` que imprime, inicia sesión
con el magic-link, graba una nota y aparecerá en la lista de hoy.

## Apagado seguro

**Backend / Telegram** — evita que Telegram bloquee el bot por reintentos contra
una URL muerta:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_TOKEN>/deleteWebhook"
```
Luego detén Uvicorn (`Ctrl + C`) y Ngrok (`Ctrl + C`).

**PWA** — basta con `Ctrl + C` en las dos terminales: primero el túnel
(`cloudflared`) y después Vite (`npm run dev`). Al cerrar el túnel, la URL
`trycloudflare.com` deja de existir (son efímeras), así que no hay nada que
revocar.

## Tests

Pocos tests por metodología (un test por caso límite, sin suite exhaustiva).
Toda la suite de golpe:

```bash
uv run pytest
```

La suite cubre:

| Archivo | Qué prueba |
| --- | --- |
| `test_registration_pipeline.py` | el FLUJO A de punta a punta (con puertos falsos) |
| `test_validation_service.py` | validación legal (dosis, área, producto autorizado) |
| `test_schemas.py` | `ExtractedFields` (saneado de la salida del LLM) |
| `test_serialize_columns.py` | modelo de dominio ↔ columnas de la BD (sin drift) |
| `test_fuzzy_lookup.py` | búsqueda difusa de parcela/producto/equipo por alias |
| `test_states.py` | transiciones de la máquina de estados |
| `test_auth.py` | verificación del JWT de Supabase (`current_advisor_id`) |
| `test_api.py` | endpoints y mapeo de errores a `{error, mensaje}` |

Para un archivo suelto: `uv run pytest tests/test_registration_pipeline.py`.
