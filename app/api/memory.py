"""
Zave User Memory Retrieval API
This module provides high-performance access to the processed behavioral profiles.
It implements a Cache-Aside pattern using Redis for sub-10ms response times.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.models.memory import UserMemory
from app.middleware.auth import verify_api_key
from app.services.memory import memory_service
from app.services.cache import cache_service
from app.db.mongo import db

router = APIRouter(prefix="/users", tags=["Memory"])

@router.get("/{user_id}/memory", response_model=UserMemory, dependencies=[Depends(verify_api_key)])
async def get_user_memory(user_id: str):
    """
    Retrieves the 4-layer behavioral memory profile for a specific user.
    
    The API first checks the Redis Cache for an immediate hit. 
    If missing, it falls back to MongoDB and repopulates the cache.
    """
    
    # --- PHASE 1: Redis Cache Lookup ---
    # We prioritize the cache to maintain lightning-fast response times for the UI.
    cached_data = await cache_service.get_memory(user_id)
    
    if cached_data:
        # If found in Redis, we return immediately. This usually takes < 5ms.
        return UserMemory(**cached_data)

    # --- PHASE 2: MongoDB Fallback ---
    # If the cache is empty (Cache Miss), we query our primary persistent store.
    memory_doc = await db["user_memories"].find_one({"user_id": user_id})
    
    if not memory_doc:
        # If the user has zero history, we return a 404.
        raise HTTPException(status_code=404, detail="Memory not found for user")

    # --- PHASE 3: Cache Repopulation ---
    # We save the MongoDB result back into Redis so the NEXT request is fast.
    await cache_service.set_memory(user_id, memory_doc)
    
    return UserMemory(**memory_doc)
