"""
Quick throwaway script to validate OpenRouter LLM output.

Tests that free models return valid, parseable JSON matching 
our expected memory extraction schema.

Usage:
    pip install openai python-dotenv
    # Ensure .env has OPENROUTER_API_KEY
    python scripts/test_llm_prompt.py
"""
import json
import os
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI

# Load .env file
load_dotenv()

# --- Config ---
API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"

# List of free models to try (Confirmed active by user)
MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "qwen/qwen3-coder:free",
    "minimax/minimax-m2.5:free",
    "google/gemini-2.0-flash-exp:free",
]

if not API_KEY:
    print("ERROR: Set OPENROUTER_API_KEY in .env file.")
    sys.exit(1)

client = OpenAI(
    api_key=API_KEY, 
    base_url=BASE_URL,
    default_headers={
        "HTTP-Referer": "https://github.com/zave/zave-memory-system",
        "X-Title": "Zave Memory System",
    }
)

# --- The exact system prompt we'll use in production ---
SYSTEM_PROMPT = """You are a user behavior analyst for a mobile commerce app. Your job is to extract structured behavioral signals from raw user activity data.

You MUST respond with valid JSON only. No preamble, no markdown, no explanation, no code fences. ONLY raw JSON.

Output format:
{
  "results": [
    {
      "user_id": "string",
      "persistent_updates": {
        "name": "string or null",
        "location": "string or null",
        "preferred_language": "string or null",
        "device_type": "string or null"
      },
      "episodic_events": [
        {
          "description": "short human-readable description of what happened",
          "event_type": "view | click | search | purchase | comparison | wishlist | browse"
        }
      ],
      "inferred_preferences": ["string"],
      "contextual_signals": {
        "time_of_day": "morning | afternoon | evening | night",
        "session_type": "browse | research | purchase"
      }
    }
  ]
}

Rules:
- Extract ONLY what is clearly present in the data. Do not invent information.
- If a persistent field (name, location, etc.) is not mentioned, set it to null.
- Keep episodic event descriptions short and specific.
- Inferred preferences should be brief strings like "prefers cashback" or "price sensitive".
- If the data mentions multiple users, include a result object for each user."""

# --- Test payloads that simulate real mobile activity ---
TEST_PAYLOADS = [
    {
        "user_id": "user_abc123",
        "raw_data": "User opened app on Android device in Mumbai at 10:32 PM. Browsed electronics category for 2 minutes. Clicked on iPhone 15 Pro Max listing. Spent 45 seconds reading reviews. Added to wishlist. Searched for 'samsung s24 ultra price'. Compared iPhone 15 Pro Max vs Samsung S24 Ultra. Closed comparison without purchase."
    },
    {
        "user_id": "user_xyz789",
        "raw_data": "User on iOS device, location Delhi. Searched 'best wireless earbuds under 2000'. Viewed JBL Tune 230NC product page for 30 seconds. Checked 3 cashback offers. Applied cashback coupon. Purchased JBL Tune 230NC for Rs 1899 with Rs 200 cashback. Payment via UPI."
    },
    {
        "user_id": "user_test456",
        "raw_data": "User browsing from Bangalore on Android. Viewed home page. Scrolled through deals section. Clicked on 'weekend sale' banner. Viewed 5 products in groceries category. Added Tata Salt and Aashirvaad Atta to cart. Removed Tata Salt from cart. Did not complete purchase. Session lasted 4 minutes."
    },
]


def call_llm(user_msg: str, max_tokens: int = 1000) -> str | None:
    """Try various free models until one works."""
    for model in MODELS:
        print(f"  Trying model: {model}...")
        start = time.time()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
                max_tokens=max_tokens,
            )
            elapsed = time.time() - start
            raw = response.choices[0].message.content.strip()
            print(f"    Success! ({elapsed:.2f}s)")
            return raw
        except Exception as e:
            err_msg = str(e)
            print(f"    FAILED: {err_msg[:80]}...")
            continue
    return None


def validate_response(raw_output: str) -> dict | None:
    """Parse and validate the raw LLM JSON output."""
    try:
        parsed = json.loads(raw_output)
        print(f"  JSON parse: ✅ VALID")
    except json.JSONDecodeError as e:
        print(f"  JSON parse: ❌ FAILED — {e}")
        return None

    if "results" not in parsed:
        print(f"  Structure: ❌ Missing 'results' key")
        return None

    results = parsed["results"]
    if not isinstance(results, list) or len(results) == 0:
        print(f"  Structure: ❌ 'results' is not a non-empty array")
        return None

    result = results[0]
    required_keys = ["user_id", "persistent_updates", "episodic_events"]
    missing = [k for k in required_keys if k not in result]
    if missing:
        print(f"  Structure: ❌ Missing keys: {missing}")
        return None

    print(f"  Structure: ✅ VALID")
    return parsed


if __name__ == "__main__":
    print("=" * 60)
    print(f"LLM Prompt Validation — OpenRouter")
    print(f"Models to check: {MODELS}")
    print("=" * 60)

    all_passed = True
    
    # 1. Individual tests
    for payload in TEST_PAYLOADS:
        print(f"\n--- Testing user_id: {payload['user_id']} ---")
        user_msg = f"Analyze this user activity record:\n{json.dumps([payload])}"
        raw_output = call_llm(user_msg)
        
        if raw_output:
            result = validate_response(raw_output)
            if result:
                # Brief visual check
                extracted = result["results"][0]
                uid = extracted.get("user_id")
                events = extracted.get("episodic_events", [])
                print(f"    [OK] uid: {uid}, events: {len(events)}")
            else:
                all_passed = False
        else:
            print(f"  ❌ All models failed for this user.")
            all_passed = False

    # 2. Batch test
    print("\n" + "=" * 60)
    print("BATCH TEST — 3 events in one call")
    print("=" * 60)
    
    batch_msg = f"Analyze these user activity records:\n{json.dumps(TEST_PAYLOADS)}"
    batch_raw = call_llm(batch_msg, max_tokens=2000)
    
    if batch_raw:
        batch_result = validate_response(batch_raw)
        if batch_result:
            count = len(batch_result.get("results", []))
            print(f"    [OK] Batch results count: {count} (expected: 3)")
            if count != 3:
                all_passed = False
        else:
            all_passed = False
    else:
        print(f"  ❌ All models failed for batch test.")
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED — Prompt is production-ready.")
        print("   Proceed to Phase 2 (infrastructure build).")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
