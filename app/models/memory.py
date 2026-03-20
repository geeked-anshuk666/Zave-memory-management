"""
Zave Cognitive Memory Models
This is the core data structure of the Zave ecosystem. 
It defines the 4 layers of human-like memory: Persistent, Episodic, Semantic, and Contextual.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PersistentMemory(BaseModel):
    """
    LAYER 1: Persistent Memory
    Stores long-term, slow-changing user traits and preferences.
    Example: 'Loves high-end electronics' or 'Prefers budget clothing'.
    """
    preferred_categories: List[str] = Field(default_factory=list)
    price_sensitivity: Optional[str] = None
    last_active_time_of_day: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class EpisodicMemory(BaseModel):
    """
    LAYER 2: Episodic Memory
    Stores a chronological timeline of specific events.
    Example: 'User viewed a MacBook Pro' followed by 'User added it to cart'.
    """
    event_type: str
    summary: str
    sentiment: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UserMemory(BaseModel):
    """
    The Master Cognitive Profile.
    This object is what the Recommendation Engine reads to personalize the storefront.
    """
    
    user_id: str = Field(..., description="The unique key for this user identity")

    # Layer 1: Long-term traits
    persistent: PersistentMemory = Field(default_factory=PersistentMemory)

    # Layer 2: Chronological action history (Bounded to prevent database bloat)
    episodic: List[EpisodicMemory] = Field(
        default_factory=list, 
        description="A rolling window of the last 100 historical events"
    )

    # Layer 3: Semantic Interests
    # Deduplicated tags representing the 'concepts' the user cares about.
    semantic_interests: List[str] = Field(
        default_factory=list, 
        description="Set of inferred high-level interests (e.g., 'Gaming', 'Fitness')"
    )

    # Layer 4: Contextual Summary
    # A short-term, session-based summary of what the user is currently looking for.
    contextual_summary: Optional[str] = Field(
        None, 
        description="Short-term focus (e.g., 'Searching for a gift for a child')"
    )
    
    version: int = Field(1, description="Increments on every processing cycle")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
