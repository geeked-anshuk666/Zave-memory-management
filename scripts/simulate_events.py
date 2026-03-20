import httpx
import asyncio
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

API_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY")

TEST_USER_ID = f"test_user_{uuid.uuid4().hex[:8]}"

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

async def send_event(event):
    headers = {"X-API-Key": API_KEY}
    async with httpx.AsyncClient() as client:
        print(f"Sending raw event for user {event['user_id']}...")
        response = await client.post(f"{API_URL}/events", json=event, headers=headers)
        if response.status_code == 200:
            print(f"--Success: {response.json()['event_id']}")
        else:
            print(f"----Error {response.status_code}: {response.text}")

async def get_raw_history(user_id):
    headers = {"X-API-Key": API_KEY}
    async with httpx.AsyncClient() as client:
        print(f"\nRetrieving raw data lake logs for user {user_id}...")
        response = await client.get(f"{API_URL}/events/raw/{user_id}", headers=headers)
        if response.status_code == 200:
            events = response.json()
            print("--- RAW UNSTRUCTURED DATA LAKE ---")
            print(json.dumps(events, indent=2))
        else:
            print(f"----Error {response.status_code}: {response.text}")

async def get_memory(user_id):
    headers = {"X-API-Key": API_KEY}
    async with httpx.AsyncClient() as client:
        print(f"\nRetrieving memory for user {user_id}...")
        response = await client.get(f"{API_URL}/users/{user_id}/memory", headers=headers)
        if response.status_code == 200:
            memory = response.json()
            print("--- MEMORY PROFILE ---")
            print(json.dumps(memory, indent=2))
        else:
            print(f"------ Error {response.status_code}: {response.text}")

async def main():
    print(f"Starting test simulation for user: {TEST_USER_ID}")
    
    # Send events
    for event in TEST_EVENTS:
        await send_event(event)
        await asyncio.sleep(0.5) # Small gap
    
    print("\nEvents sent. Waiting for async processing (Celery + LLM)...")
    
    # Poll for memory profile since free-tier LLMs can take up to 30s
    max_retries = 15
    for attempt in range(max_retries):
        await asyncio.sleep(3)
        headers = {"X-API-Key": API_KEY}
        try:
            # We silently check if the memory is ready yet
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_URL}/users/{TEST_USER_ID}/memory", headers=headers)
                if response.status_code == 200:
                    break
        except Exception:
            pass
        print(f"Still waiting for LLM to finish extracting data... ({attempt * 3}s elapsed)")
    
    # Check raw data lake
    await get_raw_history(TEST_USER_ID)

    # Check memory
    await get_memory(TEST_USER_ID)

if __name__ == "__main__":
    asyncio.run(main())
