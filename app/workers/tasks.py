"""
Zave Background Worker Tasks
This module contains the Celery tasks that perform the heavy lifting of 
asynchronous behavioral analysis and memory synchronization.
"""

import asyncio
import logging
from app.workers.celery_app import celery_app
from app.services.llm import llm_service
from app.services.memory import memory_service
from app.services.cache import cache_service

logger = logging.getLogger(__name__)

@celery_app.task(name="app.workers.tasks.process_event")
def process_event(event_data: dict):
    """
    The main processing pipeline for every user event.
    
    Workflow:
    1. Extract behavioral signals using the LLM (Cognitive Step)
    2. Atomic update to the 4-layer memory model in MongoDB (Persistence Step)
    3. Invalidate the Redis cache to ensure the next GET request is fresh (Consistency Step)
    """
    
    event_id = event_data.get("event_id")
    user_id = event_data.get("user_id")
    
    logger.info(f"--- Starting Processing for Event: {event_id} (User: {user_id}) ---")
    
    # We use a custom event loop to run our async service methods within 
    # the synchronous context of a Celery worker.
    loop = asyncio.get_event_loop()
    
    # --- PHASE 1: LLM Behavioral Extraction ---
    # We send the raw event payload to the LLM to 'understand' what the user did.
    behavioral_data = loop.run_until_complete(llm_service.extract_behavioral_data(event_data))
    
    if not behavioral_data:
        logger.error(f"Failed to extract behavioral data for event {event_id}")
        return {"status": "failed", "reason": "llm_extraction_failed"}
    
    logger.info(f"Successfully extracted behavioral data for user {user_id}")
    
    # --- PHASE 2: MongoDB Memory Persistence ---
    # We transition the LLM's raw dict into our structured 4-layer memory system.
    loop.run_until_complete(memory_service.update_memory(user_id, behavioral_data))
    
    # --- PHASE 3: Cache Invalidation ---
    # To keep Zave lightning fast, we serve reads from Redis. 
    # By deleting the cache here, we force the next frontend request to 
    # pull the freshly updated memory from the database.
    loop.run_until_complete(cache_service.invalidate(user_id))
    
    logger.info(f"--- Finished Processing for Event: {event_id} ---")
    
    return {
        "status": "processed", 
        "event_id": event_id, 
        "behavioral_data": behavioral_data
    }
