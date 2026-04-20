from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    REDIS_URL: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
