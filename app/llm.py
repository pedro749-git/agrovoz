from google import genai
from google.genai import types
from app.config import settings

# Instanciamos el cliente (mantiene viva la conexión)
client = genai.Client(api_key=settings.gemini_api_key)

async def generate_response(text: str, history: list[dict]) -> str:
    """Mantiene la conversación usando el nuevo SDK asíncrono de Google."""
    
    formatted_history = []
    for m in history:
        role = "user" if m["role"] == "user" else "model"
        content = types.Content(role=role, parts=[types.Part.from_text(text=m["content"])])
        formatted_history.append(content)
        
    # Usamos client.aio para acceder a las funciones asíncronas
    chat = client.aio.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction="Eres Olek, un asistente técnico inteligente. Responde de forma clara y directa.",
            temperature=0.3,
        ),
        history=formatted_history
    )
    
    # Pedimos la respuesta completa de un solo golpe (ideal para bots de mensajería)
    response = await chat.send_message(text)
    
    return response.text