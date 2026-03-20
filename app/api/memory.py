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
    Retrieves the 4-layer behavioral memory for a user.
    Uses Redis caching for sub-10ms retrieval.
    """
    # 1. Check Redis Cache
    cached_data = await cache_service.get_memory(user_id)
    if cached_data:
        return UserMemory(**cached_data)

    # 2. Cache Miss - Query MongoDB
    memory_doc = await db["user_memories"].find_one({"user_id": user_id})
    if not memory_doc:
        raise HTTPException(status_code=404, detail="Memory not found for user")

    # 3. Update Cache & Return
    await cache_service.set_memory(user_id, memory_doc)
    return UserMemory(**memory_doc)
