"""
Zave Global Configuration
Uses Pydantic Settings to manage environment variables with strict typing.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    All application secrets and connection strings are centralized here.
    These can be overridden by creating a .env file or setting system env vars.
    """
    
    # --- Infrastructure Connections ---
    REDIS_URI: str = "redis://redis:6379/0"
    MONGODB_URI: str = "mongodb://mongodb:27017"

    # --- Security & Intelligence ---
    API_KEY: str = "default_secret_key"
    OPENROUTER_API_KEY: str = ""

    # --- Behavioral Tuning ---
    # Bounds the episodic memory to the last 100 events for optimal document sizing
    MAX_EPISODIC_EVENTS: int = -100

    # Pydantic configuration: link to .env and ignore unknown extra variables
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Static singleton to be imported by other modules
settings = Settings()
