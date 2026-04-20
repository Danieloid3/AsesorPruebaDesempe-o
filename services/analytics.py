from core.db import supabase

def save_chat_log(log_data: dict) -> None:
    """Saves a conversation interaction and its metrics to Supabase."""
    try:
        supabase.table("chat_logs").insert(log_data).execute()
    except Exception as e:
        # We catch exceptions so that analytics failures don't break the user experience
        print(f"Error guardando logs en Supabase: {e}")
