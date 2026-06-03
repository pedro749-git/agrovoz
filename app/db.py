from supabase import create_async_client, AsyncClient
from app.config import settings

# Variable global oculta para guardar el cliente una vez creado
_supabase_client: AsyncClient | None = None

async def get_supabase() -> AsyncClient:
    """Inicializa el cliente de forma segura y lo reutiliza (Singleton)."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = await create_async_client(
            settings.supabase_url, 
            settings.supabase_service_key
        )
    return _supabase_client

async def save_message(user_id: int, role: str, content: str) -> None:
    """Inserta un mensaje en la BD sin esperar a que el LLM responda."""
    client = await get_supabase()
    await client.table("messages").insert({
        "telegram_user_id": user_id,
        "role": role,
        "content": content
    }).execute()

async def get_history(user_id: int, limit: int = 5) -> list[dict]:
    """Recupera el contexto histórico para la IA."""
    client = await get_supabase()
    res = await client.table("messages") \
        .select("role, content") \
        .eq("telegram_user_id", user_id) \
        .order("created_at", desc=True) \
        .limit(limit) \
        .execute()
    
    # Invertimos la lista [::-1] para que la IA lea del más antiguo al más nuevo
    return res.data[::-1]