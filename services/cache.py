import json
from core.db import redis_client
import re

CACHE_TTL = 86400  # 24 hours in seconds

def normalize_text(text: str) -> str:
    """Normalize text to increase cache hit rate for similar questions."""
    # Convert to lowercase and strip whitespace
    text = text.lower().strip()
    # Remove extra spaces and punctuation for a normalized key
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def get_cached_response(query: str) -> dict | None:
    """Check if the answer is already in Redis cache."""
    normalized = normalize_text(query)
    cache_key = f"chat_cache:{normalized}"

    cached_data = redis_client.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    return None

def set_cached_response(query: str, response_data: dict) -> None:
    """Save the response to Redis with a TTL."""
    normalized = normalize_text(query)
    cache_key = f"chat_cache:{normalized}"

    # Do not cache escalations or out-of-scope cases for too long, just valid answers
    # But for MVP, let's cache everything based on the query.
    redis_client.set(cache_key, json.dumps(response_data), ex=CACHE_TTL)

def get_chat_history(user_id: str) -> list:
    """Retrieve the recent chat history for a user."""
    history_key = f"chat_history:{user_id}"
    history_data = redis_client.get(history_key)
    if history_data:
        return json.loads(history_data)
    return []

def add_to_chat_history(user_id: str, user_msg: str, ai_msg: str) -> None:
    """Add a new exchange to the user's chat history."""
    history = get_chat_history(user_id)
    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": ai_msg})
    # Keep only the last 12 messages (6 interactions) to allow for better conversation context
    if len(history) > 16:
        history = history[-16:]

    history_key = f"chat_history:{user_id}"
    redis_client.set(history_key, json.dumps(history), ex=3600)  # Expire history after 1 hour of inactivity

def log_metrics(cost: float, is_escalated: bool, is_cache_hit: bool):
    """Log simple interaction metrics to Redis."""
    try:
        redis_client.incr("metrics:total_queries")

        if is_cache_hit:
            redis_client.incr("metrics:cache_hits")
        else:
            redis_client.incrbyfloat("metrics:total_cost", cost)

        if is_escalated:
            redis_client.incr("metrics:escalations")
    except Exception as e:
        print(f"Failed to log metrics: {e}")

def get_dashboard_metrics() -> dict:
    """Retrieve simple dashboard metrics from Redis."""
    try:
        total = int(redis_client.get("metrics:total_queries") or 0)
        escalations = int(redis_client.get("metrics:escalations") or 0)
        cost = float(redis_client.get("metrics:total_cost") or 0.0)
        cache_hits = int(redis_client.get("metrics:cache_hits") or 0)

        escalation_rate = (escalations / total * 100) if total > 0 else 0.0
        cache_rate = (cache_hits / total * 100) if total > 0 else 0.0

        return {
            "total_queries": total,
            "escalation_rate_percent": round(escalation_rate, 2),
            "total_estimated_cost_usd": round(cost, 6),
            "cache_hit_rate_percent": round(cache_rate, 2)
        }
    except Exception as e:
        print(f"Failed to retrieve metrics: {e}")
        return {}
