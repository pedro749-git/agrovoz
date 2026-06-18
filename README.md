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
- [ ] M4 — PWA mínima · M5 — máquina de estados + clima AEMET · M6 — evaluación
      de eficacia · M7 — validaciones de campaña.

## Stack

Python 3.12 · FastAPI + Uvicorn · Pydantic V2 · Supabase (PostgreSQL) ·
Qwen-Audio + Qwen Instruct vía DashScope · Alibaba Cloud OSS · ReportLab.
Gestión de dependencias con `uv`.

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
```

El núcleo solo depende de puertos (ABCs): el webhook de Telegram de hoy y la PWA
de mañana llaman al **mismo** pipeline sin tocar lógica de negocio.

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

## Apagado seguro

Evita que Telegram bloquee el bot por reintentos contra una URL muerta:

```bash
curl -X POST "https://api.telegram.org/bot<TELEGRAM_TOKEN>/deleteWebhook"
```
Luego detén Uvicorn (`Ctrl + C`) y Ngrok (`Ctrl + C`).

## Tests

Pocos tests por metodología (un test por caso límite, sin suite exhaustiva).
Toda la suite de golpe:

```bash
uv run pytest
```

Cada archivo también se puede ejecutar suelto (sin pytest):

```bash
uv run python tests/test_registration_pipeline.py   # casos del FLUJO A
uv run python tests/test_serialize_columns.py        # modelo <-> columnas de la BD
uv run python tests/test_fuzzy_lookup.py             # búsqueda difusa por alias
```
