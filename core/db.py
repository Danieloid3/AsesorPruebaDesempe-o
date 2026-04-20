from supabase import create_client, Client
import redis
from core.config import settings

# Initialize Supabase client
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY
)

# Initialize Redis client
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
