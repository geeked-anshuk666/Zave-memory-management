from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class RawEvent(BaseModel):
    user_id: str = Field(..., description="Unique identifier for the user to map to memory profile")
    raw_payload: str = Field(..., description="Raw unstructured text, logs, or JSON payload. Limit to 50KB.")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class EventResponse(BaseModel):
    status: str
    message: str
    event_id: str
