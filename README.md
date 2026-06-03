# Bot de Prueba

Un bot de pruebas de Telegram asíncrono y de baja latencia diseñado para actuar como un asistente técnico inteligente. Construido con una arquitectura orientada a eventos, persistencia de memoria a corto plazo y capacidades cognitivas impulsadas por la última generación de modelos de Google. 

## 🚀 Arquitectura y Flujo de Datos

El sistema implementa un patrón "Falla Rápido" (Fail Fast) en el arranque y un procesamiento en segundo plano (Fire and Forget) para garantizar que los Webhooks de Telegram se respondan en milisegundos, evitando bloqueos por *timeouts*.

1. **Ingress:** Telegram envía un evento vía Webhook a FastAPI.
2. **Orquestación:** FastAPI responde con `HTTP 200 OK` instantáneamente y delega el payload a `BackgroundTasks`.
3. **Persistencia (Entrada):** Se guarda el mensaje del usuario en PostgreSQL (Supabase) vía su cliente asíncrono.
4. **Cognición:** Se recupera el historial reciente y se inyecta en `gemini-2.5-flash` para mantener el contexto de la conversación.
5. **Persistencia (Salida):** Se guarda la respuesta generada por la IA.
6. **Egress:** Se emite una petición POST asíncrona (`httpx`) a la API de Telegram para entregar el mensaje al usuario.

## 🛠️ Stack Tecnológico

* **Framework API:** [FastAPI](https://fastapi.tiangolo.com/) (Orquestador ASGI)
* **Gestor de Paquetes/Entorno:** [uv](https://docs.astral.sh/uv/)
* **Base de Datos:** [Supabase](https://supabase.com/) (PostgreSQL + PostgREST)
* **LLM (IA):** Google Gemini (`gemini-2.5-flash` vía `google-genai` SDK)
* **Validación de Entorno:** Pydantic Settings V2

## ⚙️ Requisitos Previos

Antes de ejecutar el proyecto, asegúrate de tener instalados:
* Python 3.10+
* `uv` (Gestor de dependencias ultrarrápido)
* `ngrok` (Para exponer el puerto local)
* Un bot registrado en [BotFather](https://t.me/botfather) (Telegram)
* Un proyecto creado en Supabase con una tabla `messages` (columnas: `id`, `created_at`, `telegram_user_id`, `role`, `content`).

## 🔐 Configuración del Entorno

```env
TELEGRAM_TOKEN=token_de_botfather
SUPABASE_URL=url_de_proyecto_supabase
SUPABASE_SERVICE_KEY=clave_secreta_service_role
GEMINI_API_KEY=clave_de_google_ai_studio
```
Ignorado con .gitignore.

## 💻 Instalación y Ejecución Local

**1. Instalar dependencias**
```bash
uv sync
```

**2. Levantar el servidor de desarrollo**
El servidor se ejecutará en el puerto 8000 con recarga automática.
```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**3. Exponer el servidor a internet**
En una nueva terminal, abre un túnel seguro con Ngrok:
```bash
ngrok http 8000
```
*(Copia la URL pública generada que empieza por `https://`)*

**4. Conectar la tubería con Telegram (Configurar Webhook)**
En otra terminal, ejecuta este comando reemplazando las variables con tus datos:
```bash
curl -X POST "[https://api.telegram.org/bot](https://api.telegram.org/bot)<TELEGRAM_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://<URL_DE_NGROK>/webhook"}'
```

¡Listo! El bot ya debería estar respondiendo a los mensajes desde la aplicación de Telegram.

## 📁 Estructura del Proyecto

```text
olek_bot_project/
├── .env                  # Variables de entorno (IGNORADO)
├── .gitignore            # Archivos excluidos del control de versiones
├── README.md             # Documentación del proyecto
├── pyproject.toml        # Dependencias y metadatos gestionados por uv
└── app/                  # Código fuente principal
    ├── main.py           # Orquestador FastAPI y endpoint del Webhook
    ├── config.py         # Validación estricta del entorno (Pydantic)
    ├── db.py             # Capa DAL asíncrona para interactuar con Supabase
    ├── llm.py            # Capa cognitiva e integración con Gemini SDK
    └── telegram.py       # Capa de comunicación saliente hacia la API de Telegram
```

## 🛑 Apagado Seguro

Para cerrar el entorno sin dejar procesos fantasma y evitar que Telegram bloquee tu bot por reintentos fallidos a una URL muerta:

1. Elimina el Webhook activo:
   ```bash
   curl -X POST "[https://api.telegram.org/bot](https://api.telegram.org/bot)<TU_TELEGRAM_TOKEN>/deleteWebhook"
   ```
2. Detén Uvicorn (`Ctrl + C`)
3. Cierra Ngrok (`Ctrl + C`)