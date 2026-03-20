from fastapi import APIRouter, Depends, BackgroundTasks
from app.models.event import RawEvent, EventResponse
from app.middleware.auth import verify_api_key
from app.middleware.validation import validate_payload_size
from app.middleware.rate_limit import rate_limit_middleware
from app.workers.tasks import process_event
from app.db.mongo import db
import uuid
import json

router = APIRouter(prefix="/events", tags=["Events"])

@router.post("", response_model=EventResponse, dependencies=[
    Depends(verify_api_key), 
    Depends(validate_payload_size),
    Depends(rate_limit_middleware)
])
async def ingest_event(event: RawEvent):
    event_id = str(uuid.uuid4())
    
    # Store raw event in data lake before processing
    raw_event_doc = event.model_dump()
    raw_event_doc["event_id"] = event_id
    raw_event_doc["received_at"] = raw_event_doc.pop("timestamp").isoformat()
    
    await db["raw_events"].insert_one(raw_event_doc)
    
    # Dispatch Celery Task with serialization-friendly data
    process_event.delay({
        "event_id": event_id,
        "user_id": event.user_id,
        "raw_payload": event.raw_payload,
        "received_at": raw_event_doc["received_at"]
    })
    
    return EventResponse(
        status="success",
        message="Raw event ingested and queued for processing",
        event_id=event_id
    )

@router.get("/raw/{user_id}", dependencies=[Depends(verify_api_key)])
async def get_raw_events(user_id: str):
    """Retrieves the history of raw unstructured events for a user."""
    cursor = db["raw_events"].find({"user_id": user_id}).sort("received_at", -1).limit(50)
    events = await cursor.to_list(length=50)
    # Convert ObjectId to string for JSON serialization
    for event in events:
        event["_id"] = str(event["_id"])
    return {"user_id": user_id, "raw_events": events}
