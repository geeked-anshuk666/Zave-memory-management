import logging
from datetime import datetime
from typing import Dict, Any
from app.db.mongo import db
from app.models.memory import UserMemory

logger = logging.getLogger(__name__)

class MemoryService:
    def __init__(self):
        self.collection = db["user_memories"]

    async def update_memory(self, user_id: str, behavioral_data: Dict[str, Any]):
        """
        Updates the 4-layer memory system in MongoDB using atomic operators.
        """
        try:
            # 1. Update Persistent Layer (Preferences)
            persistent = behavioral_data.get("persistent_updates", {})
            
            # 2. Update Episodic Layer (History) - Bounded to 100 entries
            new_episodes = behavioral_data.get("episodic_events", [])
            
            # 3. Update Semantic Layer (Interests)
            new_interests = behavioral_data.get("inferred_preferences", [])

            # Prepare Atomic Update
            update_query = {
                "$set": {
                    "updated_at": datetime.utcnow(),
                },
                "$inc": {"version": 1}
            }

            # Add Persistent updates
            if persistent:
                for key, value in persistent.items():
                    if value is not None:
                        update_query["$set"][f"persistent.{key}"] = value

            # Add Episodic updates with $slice bounding
            if new_episodes:
                update_query["$push"] = {
                    "episodic": {
                        "$each": new_episodes,
                        "$slice": -100,  # Keep only the last 100 events
                        "$sort": {"timestamp": 1}
                    }
                }

            # Add Semantic updates via $addToSet (unique interests only)
            if new_interests:
                if "$addToSet" not in update_query:
                    update_query["$addToSet"] = {}
                update_query["$addToSet"]["semantic_interests"] = {"$each": new_interests}

            # Perform Upsert
            await self.collection.update_one(
                {"user_id": user_id},
                update_query,
                upsert=True
            )
            
            logger.info(f"Successfully updated memory for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to update memory for user {user_id}: {e}")
            raise

memory_service = MemoryService()
