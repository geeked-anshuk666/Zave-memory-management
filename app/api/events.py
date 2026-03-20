from fastapi import APIRouter, Depends, BackgroundTasks
from app.models.event import UserEvent, EventResponse
from app.middleware.auth import verify_api_key
from app.middleware.validation import validate_payload_size
from app.middleware.rate_limit import rate_limit_middleware
from app.db.redis import get_redis
import uuid
import json

router = APIRouter(prefix="/events", tags=["Events"])

@router.post("", response_model=EventResponse, dependencies=[
    Depends(verify_api_key), 
    Depends(validate_payload_size),
    Depends(rate_limit_middleware)
])
async def ingest_event(event: UserEvent):
    event_id = str(uuid.uuid4())
    
    # In a real system, we'd push to a Redis queue for Celery to pick up
    # For now, we'll just acknowledge and mention Step 5 (Celery)
    
    # Prepare data for Redis Queue
    event_data = event.model_dump()
    event_data["event_id"] = event_id
    event_data["received_at"] = event.timestamp.isoformat()
    
    # Get redis client and push to list 'zave_events'
    redis = await get_redis()
    await redis.lpush("zave_events", json.dumps(event_data))
    
    return EventResponse(
        status="success",
        message="Event queued for processing",
        event_id=event_id
    )
