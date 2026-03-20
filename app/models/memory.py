from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class PersistentMemory(BaseModel):
    preferred_categories: List[str] = Field(default_factory=list)
    price_sensitivity: Optional[str] = None
    last_active_time_of_day: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class EpisodicMemory(BaseModel):
    event_type: str
    summary: str
    sentiment: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UserMemory(BaseModel):
    user_id: str

    persistent: PersistentMemory = Field(default_factory=PersistentMemory)

    episodic: List[EpisodicMemory] = Field(default_factory=list, description="Bounded to last 100 events")

    semantic_interests: List[str] = Field(default_factory=list, description="Set of inferred interests")

    contextual_summary: Optional[str] = None
    
    version: int = 1
    updated_at: datetime = Field(default_factory=datetime.utcnow)
