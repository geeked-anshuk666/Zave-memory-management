from app.workers.celery_app import celery_app
from app.services.llm import llm_service
from app.services.memory import memory_service
from app.services.cache import cache_service
import asyncio
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="app.workers.tasks.process_event")
def process_event(event_data: dict):
    """
    Background task to process e-commerce events:
    1. Extract behavioral signals using LLM (Step 6)
    2. Update multi-layered user memory in MongoDB (Step 7)
    3. Invalidate Redis cache for immediate consistency (Step 7)
    """
    event_id = event_data.get("event_id")
    user_id = event_data.get("user_id")
    
    logger.info(f"Processing event {event_id} for user {user_id}")
    
    # Run async LLM extraction in synchronous Celery task
    loop = asyncio.get_event_loop()
    behavioral_data = loop.run_until_complete(llm_service.extract_behavioral_data(event_data))
    
    if not behavioral_data:
        logger.error(f"Failed to extract behavioral data for event {event_id}")
        return {"status": "failed", "reason": "llm_extraction_failed"}
    
    logger.info(f"Successfully extracted behavioral data for user {user_id}")
    
    # 2. Update Multi-layered User Memory in MongoDB
    loop.run_until_complete(memory_service.update_memory(user_id, behavioral_data))
    
    # 3. Invalidate Redis Cache for this user
    loop.run_until_complete(cache_service.invalidate(user_id))
    
    return {"status": "processed", "event_id": event_id, "behavioral_data": behavioral_data}
