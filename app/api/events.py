from fastapi import APIRouter, Depends, BackgroundTasks
from app.models.event import UserEvent, EventResponse
from app.middleware.auth import verify_api_key
from app.middleware.validation import validate_payload_size
from app.middleware.rate_limit import rate_limit_middleware
from app.workers.tasks import process_event
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
    
    # Prepare data for processing
    event_data = event.model_dump()
    event_data["event_id"] = event_id
    event_data["received_at"] = event.timestamp.isoformat()
    
    # Dispatch Celery Task
    process_event.delay(event_data)
    
    return EventResponse(
        status="success",
        message="Event queued for processing",
        event_id=event_id
    )
