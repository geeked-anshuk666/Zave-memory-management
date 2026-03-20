from fastapi import FastAPI
from app.config import settings
from app.api.events import router as events_router
from app.api.memory import router as memory_router

app = FastAPI(
    title="Zave Memory System",
    description="Real-time user memory and behavior analysis system.",
    version="0.1.0"
)

app.include_router(events_router)
app.include_router(memory_router)

@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "version": "0.1.0",
        "debug": settings.DEBUG
    }
