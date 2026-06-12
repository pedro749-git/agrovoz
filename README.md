# Sandbox

CONSTRUCCIÓN EN PROGRESO.

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

## 🛑 Apagado Seguro

Para cerrar el entorno sin dejar procesos fantasma y evitar que Telegram bloquee tu bot por reintentos fallidos a una URL muerta:

1. Elimina el Webhook activo:
   ```bash
   curl -X POST "[https://api.telegram.org/bot](https://api.telegram.org/bot)<TU_TELEGRAM_TOKEN>/deleteWebhook"
   ```
2. Detén Uvicorn (`Ctrl + C`)
3. Cierra Ngrok (`Ctrl + C`)
