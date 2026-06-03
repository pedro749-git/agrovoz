from fastapi import FastAPI, Request, BackgroundTasks
from app.db import save_message, get_history
from app.llm import generate_response
from app.telegram import send_message

app = FastAPI(title="Olek AI Orquestador")

async def process_telegram_update(update: dict) -> None:
    """Lógica de negocio aislada en segundo plano."""
    message = update.get("message")
    
    # Filtro de seguridad: ignorar ediciones de mensajes, imágenes o audios por ahora
    if not message or "text" not in message:
        return
    
    chat_id = message["from"]["id"]
    user_text = message["text"]

    try:
        # 1. Guardar mensaje del usuario
        await save_message(chat_id, "user", user_text)
        
        # 2. Recuperar contexto de Supabase
        history = await get_history(chat_id)
        
        # 3. Pensar la respuesta (LLM)
        bot_response = await generate_response(user_text, history)
        
        # 4. Guardar respuesta del asistente
        await save_message(chat_id, "assistant", bot_response)
        
        # 5. Enviar mensaje a Telegram
        await send_message(chat_id, bot_response)
    
    except Exception as e:
        print(f"Error crítico procesando mensaje de {chat_id}: {e}")
        # Manejo de errores amigable sin dejar al usuario en "visto"
        await send_message(chat_id, "Mi núcleo de procesamiento está saturado. Intenta de nuevo en unos segundos.")


@app.post("/webhook")
async def telegram_webhook(request: Request, bg_tasks: BackgroundTasks):
    """
    Punto de entrada de Telegram.
    Regla de oro: Leer el JSON, encolar la tarea y devolver HTTP 200 INMEDIATAMENTE.
    """
    update = await request.json()
    
    bg_tasks.add_task(process_telegram_update, update)
    
    return {"status": "ok"}