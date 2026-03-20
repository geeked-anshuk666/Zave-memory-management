from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    REDIS_URI: str = "redis://redis:6379/0"
    MONGODB_URI: str = "mongodb://mongodb:27017"
    API_KEY: str = "default_secret_key"
    OPENROUTER_API_KEY: str = ""
    MAX_EPISODIC_EVENTS: int = -100

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
