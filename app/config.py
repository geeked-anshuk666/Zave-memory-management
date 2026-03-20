from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # API
    PORT: int = 8000
    API_KEY: str = "dev_secret_key"
    
    # LLM
    OPENROUTER_API_KEY: str
    
    # DB
    MONGO_URI: str = "mongodb://localhost:27017"
    REDIS_URI: str = "redis://localhost:6379/0"
    
    # App
    DEBUG: bool = False
    DATABASE_NAME: str = "zave_memory"
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
