from fastapi import Request, HTTPException
from app.db.redis import get_redis
import starlette.status as status
import time

RATE_LIMIT_ROUTE = "rate_limit:events"
MAX_REQUESTS = 100
WINDOW_SECONDS = 60

async def rate_limit_middleware(request: Request):
    # For now, we rate limit globally for simplicity, but could be per IP/API Key
    # Using a fixed window counter for speed
    
    redis = await get_redis()
    current_minute = int(time.time() / 60)
    key = f"{RATE_LIMIT_ROUTE}:{current_minute}"
    
    # Increment count for this minute
    count = await redis.incr(key)
    
    if count == 1:
        # First request in this window, set expiry
        await redis.expire(key, WINDOW_SECONDS)
    
    if count > MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {MAX_REQUESTS} requests per minute allowed."
        )
