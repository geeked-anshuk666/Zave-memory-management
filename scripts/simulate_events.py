"""
Zave Demo Simulation Script
This script provides an automated, end-to-end walkthrough of the Zave Memory System.
It mimics real-world e-commerce activity and verifies the background analytical pipeline.
"""

import httpx
import asyncio
import json
import uuid
import os
from datetime import datetime
from dotenv import load_dotenv

# Load credentials from .env for secure API access
load_dotenv()

API_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY")

# We generate a unique user ID for every test run to ensure a clean demo
TEST_USER_ID = f"test_user_{uuid.uuid4().hex[:8]}"

# --- MOCK DATA: REAL-WORLD SIGNALS ---
# These payloads simulate the 'messy' data found in storefront logs.
TEST_EVENTS = [
    {
        "user_id": TEST_USER_ID,
        "raw_payload": "User browsed the high-end electronics category for 12 minutes. Hovered extensively over the laptop_pro_2024 model priced at $2499.00 but did not add to cart."
    },
    {
        "user_id": TEST_USER_ID,
        "raw_payload": "LOG_ENTRY: user action=add_to_cart, item=laptop_pro_2024, context=\"User ultimately decided to purchase, indicating low price sensitivity.\""
    },
    {
        "user_id": TEST_USER_ID,
        "raw_payload": "User also checked out mechanical_keyboard_x under Accessories. Cost is 150 bucks."
    }
]

async def send_event(event: dict):
    """Hits the Zave Ingestion Gateway with a raw behavioral signal."""
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient() as client:
        print(f"-> Sending raw event for user {event['user_id']}...")
        response = await client.post(f"{API_URL}/events", json=event, headers=headers)
        
        if response.status_code == 200:
            print(f"   --Success: {response.json()['event_id']}")
        else:
            print(f"   ----Error {response.status_code}: {response.text}")

async def get_raw_history(user_id: str):
    """Retrieves the 'Source of Truth' from our MongoDB raw data lake."""
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient() as client:
        print(f"\n[STORMABR] Fetching raw data lake logs for user {user_id}...")
        response = await client.get(f"{API_URL}/events/raw/{user_id}", headers=headers)
        
        if response.status_code == 200:
            events = response.json()
            print("--- DATA LAKE: IMMUTABLE AUDIT TRAIL ---")
            print(json.dumps(events, indent=2))
        else:
            print(f"----Error {response.status_code}: {response.text}")

async def get_memory(user_id: str):
    """Retrieves the processed, structured cognitive profile for the user."""
    headers = {"X-API-Key": API_KEY}
    
    async with httpx.AsyncClient() as client:
        print(f"\n[COGNITIVE] Fetching memory profile for user {user_id}...")
        response = await client.get(f"{API_URL}/users/{user_id}/memory", headers=headers)
        
        if response.status_code == 200:
            memory = response.json()
            print("--- MEMORY PROFILE: STRUCTURED INSIGHTS ---")
            print(json.dumps(memory, indent=2))
        else:
            print(f"------ Error {response.status_code}: {response.text}")

async def main():
    """
    Main Demo Orchestrator.
    It fires the events, waits for the AI to 'think', and then proves the results.
    """
    print(f"=== Zave System Demo: {TEST_USER_ID} ===\n")
    
    # 1. Ingest all mock behavioral signals
    for event in TEST_EVENTS:
        await send_event(event)
        await asyncio.sleep(0.5) 
    
    print("\n[PIPELINE] Events queued! Now waiting for Celery + LLM to parse them...")
    
    # --- INTELLIGENT POLLING ---
    # Since we use free-tier LLMs, processing can be slow. 
    # This loop polls the API every 3s until the memory is actually ready.
    max_retries = 15
    for attempt in range(max_retries):
        await asyncio.sleep(3)
        headers = {"X-API-Key": API_KEY}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_URL}/users/{TEST_USER_ID}/memory", headers=headers)
                if response.status_code == 200:
                    print(f"\n[DONE] Intelligence processing complete after {attempt * 3}s!")
                    break
        except Exception:
            pass
        
        print(f"   ...AI is still processing the raw signals... ({attempt * 3}s elapsed)")
    
    # 2. Show the Audit Trail (The Lake)
    await get_raw_history(TEST_USER_ID)

    # 3. Show the Final Identity (The Memory)
    await get_memory(TEST_USER_ID)

if __name__ == "__main__":
    asyncio.run(main())
