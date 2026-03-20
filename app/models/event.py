"""
Zave Event Models
Defines the schema for raw data ingestion and API responses.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class RawEvent(BaseModel):
    """
    Represents an incoming behavioral signal from a client application.
    This is the model used for the Data Lake ingestion.
    """
    
    user_id: str = Field(
        ..., 
        description="Unique identifier for the user to map to their behavioral memory profile"
    )
    
    raw_payload: str = Field(
        ..., 
        description="Raw unstructured text, logs, or JSON payload from the storefront. Limit to 50KB."
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="The time the event occurred in the client application"
    )

class EventResponse(BaseModel):
    """
    Standardize the success response when an event is accepted by the Zave gateway.
    """
    
    status: str = Field(..., description="Success or failure status")
    message: str = Field(..., description="Human-readable feedback for the developer")
    event_id: str = Field(..., description="Unique UUID for tracking this event through the pipeline")
