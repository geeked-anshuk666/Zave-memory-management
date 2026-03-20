import logging
from datetime import datetime
from typing import Dict, Any

from app.db.mongo import db
from app.models.memory import UserMemory, EpisodicMemory
from pydantic import ValidationError
from app.config import settings

logger = logging.getLogger(__name__)

class MemoryService:
    """
    MemoryService is responsible for orchestrating the 4-layer memory model in MongoDB.
    It takes extracted insights from the LLM and applies them atomically to the 
    user's persistent profile using advanced MongoDB operators ($set, $push, $addToSet).
    """

    def __init__(self):
        # We target the 'user_memories' collection as our primary store for structured identity
        self.collection = db["user_memories"]

    async def update_memory(self, user_id: str, behavioral_data: Dict[str, Any]):
        """
        The core update loop. It transforms a raw dictionary of LLM insights into 
        a validated, atomic database update.
        """
        try:
            # --- PHASE 1: Data Extraction from LLM Payload ---
            
            # Persistent updates: Long-term traits like price sensitivity
            persistent = behavioral_data.get("persistent_updates", {})
            
            # Episodic events: A chronological log of what the user actually DID
            new_episodes = behavioral_data.get("episodic_events", [])
            
            # Semantic interests: Broad categories the user is gravitating towards
            new_interests = behavioral_data.get("inferred_preferences", [])

            # --- PHASE 2: Atomic Query Preparation ---
            
            # We use a single 'update_one' call to ensure thread-safety and performance
            update_query = {
                "$set": {
                    "updated_at": datetime.utcnow(),
                },
                "$inc": {"version": 1} # Track document version for history/debugging
            }

            # 1. Update Persistent Layer
            # We map specific keys (like 'price_sensitivity') into the 'persistent' nested object
            if persistent:
                for key, value in persistent.items():
                    if value is not None:
                        update_query["$set"][f"persistent.{key}"] = value

            # 2. Update Episodic Layer (The Timeline)
            # We enforce strict Pydantic validation here to prevent LLM hallucinations 
            # from corrupting our database schema.
            if new_episodes:
                valid_episodic = []
                for item in new_episodes:
                    try:
                        if isinstance(item, dict):
                            # Auto-inject server timestamp if the LLM forgot to provide one
                            if "timestamp" not in item or item.get("timestamp") is None:
                                item["timestamp"] = datetime.utcnow().isoformat()
                            
                            # Validate against our strict EpisodicMemory model
                            valid_item = EpisodicMemory(**item)
                            valid_episodic.append(valid_item.model_dump(mode='python'))
                    except ValidationError as e:
                        logger.warning(f"Invalid episodic event for user {user_id}: {item}. Error: {e}")
                        continue
                
                if valid_episodic:
                    # We 'push' new events, 'sort' them by time, and 'slice' to keep only the last 100
                    # This prevents the MongoDB document from growing infinitely.
                    update_query["$push"] = {
                        "episodic": {
                            "$each": valid_episodic,
                            "$slice": settings.MAX_EPISODIC_EVENTS,
                            "$sort": {"timestamp": 1}
                        }
                    }

            # 3. Update Semantic Layer (Unique Interests)
            # We use $addToSet so that duplicate interests (like 'Laptops') aren't added twice.
            if new_interests:
                if "$addToSet" not in update_query:
                    update_query["$addToSet"] = {}
                update_query["$addToSet"]["semantic_interests"] = {"$each": new_interests}

            # --- PHASE 3: Database Execution ---
            
            # Upsert=True ensures that if this is the user's first visit, their profile is created automatically.
            await self.collection.update_one(
                {"user_id": user_id},
                update_query,
                upsert=True
            )
            
            logger.info(f"Successfully updated memory for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to update memory for user {user_id}: {e}")
            raise

# Singleton instance for easy import across the app
memory_service = MemoryService()
