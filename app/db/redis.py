"""
Zave Redis Connector
Provides a centralized, asynchronous client for our caching and task-queueing layers.
"""

import redis.asyncio as redis
from app.config import settings

# We initialize a single Redis connection pool to be used across the application.
# decode_responses=True ensures that we get Python strings instead of raw bytes.
redis_client = redis.from_url(settings.REDIS_URI, decode_responses=True)

async def get_redis():
    """Returns the global async Redis client."""
    return redis_client
