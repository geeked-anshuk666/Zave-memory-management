"""
Zave Cache Service
Implements the high-speed 'Read-Aside' logic for user memory retrieval.
This ensures Zave can provide sub-10ms personalization for millions of users.
"""

import json
import logging
from typing import Optional, Dict, Any

from app.db.redis import get_redis

logger = logging.getLogger(__name__)

class CacheService:
    """
    CacheService handles the low-level lifecycle of Redis keys.
    It focuses on immediate consistency and extreme speed.
    """

    def __init__(self, prefix: str = "user_memory"):
        self.prefix = prefix
        self.ttl = 300  # Data lives in Redis for 5 minutes of inactivity

    def _make_key(self, user_id: str) -> str:
        """Standardizes our internal Redis naming convention."""
        return f"{self.prefix}:{user_id}"

    async def get_memory(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a pre-structured memory profile from Redis."""
        try:
            redis = await get_redis()
            data = await redis.get(self._make_key(user_id))
            
            if data:
                # If hit, we deserialize our JSON string back into a Python dict
                return json.loads(data)
                
        except Exception as e:
            logger.warning(f"Cache read error for user {user_id}: {e}")
        return None

    async def set_memory(self, user_id: str, memory_data: Dict[str, Any]):
        """Saves a fresh memory profile into Redis with a 5-minute lifespan."""
        try:
            redis = await get_redis()
            
            # setex = 'Set with Expiry'. This keeps Redis from growing infinitely.
            await redis.setex(
                self._make_key(user_id),
                self.ttl,
                json.dumps(memory_data)
            )
        except Exception as e:
            logger.warning(f"Cache write error for user {user_id}: {e}")

    async def invalidate(self, user_id: str):
        """
        Forces a cache deletion. 
        This is called by the analytical worker whenever a new event is processed.
        """
        try:
            redis = await get_redis()
            await redis.delete(self._make_key(user_id))
            
        except Exception as e:
            logger.warning(f"Cache invalidation error for user {user_id}: {e}")

# Singleton instance for simple cross-app caching
cache_service = CacheService()
