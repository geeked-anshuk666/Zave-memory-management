"""
Zave Event Ingestion API
This module serves as the primary gateway for all user behavioral data. 
It handles the storage of raw data into the Data Lake and queues background tasks for analysis.
"""

import uuid
import json
from fastapi import APIRouter, Depends, BackgroundTasks

from app.models.event import RawEvent, EventResponse
from app.middleware.auth import verify_api_key
from app.middleware.validation import validate_payload_size
from app.middleware.rate_limit import rate_limit_middleware
from app.workers.tasks import process_event
from app.db.mongo import db

router = APIRouter(prefix="/events", tags=["Events"])

@router.post("", response_model=EventResponse, dependencies=[
    Depends(verify_api_key), 
    Depends(validate_payload_size),
    Depends(rate_limit_middleware)
])
async def ingest_event(event: RawEvent):
    """
    Ingests a raw behavioral event (unstructured text or JSON).
    
    1. Generates a unique event ID for tracking.
    2. Persists the exact raw payload into the 'Data Lake' (raw_events collection).
    3. Offloads the heavy LLM analysis to a Celery worker.
    """
    event_id = str(uuid.uuid4())
    
    # --- PHASE 1: Data Lake Storage ---
    # We save the raw input immediately to ensure we never lose the 'source of truth'.
    raw_event_doc = event.model_dump()
    raw_event_doc["event_id"] = event_id
    
    # We normalize the timestamp for easier retrieval later
    raw_event_doc["received_at"] = raw_event_doc.pop("timestamp").isoformat()
    
    await db["raw_events"].insert_one(raw_event_doc)
    
    # --- PHASE 2: Background Task Dispatch ---
    # We 'fire and forget' the event data into a Redis queue. 
    # This keeps the API response time extremely low for the client app.
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
    """
    Retrieves the chronological Data Lake history for a specific user.
    Useful for developers to audit what the AI is actually reading.
    """
    # Look up the 50 most recent raw inputs
    cursor = db["raw_events"].find({"user_id": user_id}).sort("received_at", -1).limit(50)
    events = await cursor.to_list(length=50)
    
    # MongoDB returns 'ObjectId' which isn't JSON serializable by default
    for event in events:
        event["_id"] = str(event["_id"])
        
    return {
        "user_id": user_id, 
        "raw_events": events
    }
