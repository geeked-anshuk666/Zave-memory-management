from fastapi import FastAPI
from app.config import settings

app = FastAPI(
    title="Zave Memory System",
    description="Real-time user memory and behavior analysis system.",
    version="0.1.0"
)

@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "version": "0.1.0",
        "debug": settings.DEBUG
    }
