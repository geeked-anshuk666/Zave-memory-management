import json
import logging
from typing import Optional, Dict, Any
from app.db.redis import get_redis

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, prefix: str = "user_memory"):
        self.prefix = prefix
        self.ttl = 300  # 5 minutes default

    def _make_key(self, user_id: str) -> str:
        return f"{self.prefix}:{user_id}"

    async def get_memory(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached memory from Redis."""
        try:
            redis = await get_redis()
            data = await redis.get(self._make_key(user_id))
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache read error for user {user_id}: {e}")
        return None

    async def set_memory(self, user_id: str, memory_data: Dict[str, Any]):
        """Caches memory in Redis."""
        try:
            redis = await get_redis()
            await redis.setex(
                self._make_key(user_id),
                self.ttl,
                json.dumps(memory_data)
            )
        except Exception as e:
            logger.warning(f"Cache write error for user {user_id}: {e}")

    async def invalidate(self, user_id: str):
        """Removes memory from cache."""
        try:
            redis = await get_redis()
            await redis.delete(self._make_key(user_id))
        except Exception as e:
            logger.warning(f"Cache invalidation error for user {user_id}: {e}")

cache_service = CacheService()
