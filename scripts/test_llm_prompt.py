"""
Quick throwaway script to validate OpenRouter LLM output.

Tests that meta-llama/llama-3.1-8b-instruct:free returns valid,
parseable JSON matching our expected memory extraction schema.

Usage:
    pip install openai
    export OPENROUTER_API_KEY=sk-or-...
    python scripts/test_llm_prompt.py
"""
import json
import os
import sys
import time

from openai import OpenAI

# --- Config ---
API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"
MODEL = "meta-llama/llama-3.1-8b-instruct:free"

if not API_KEY:
    print("ERROR: Set OPENROUTER_API_KEY environment variable first.")
    print("  export OPENROUTER_API_KEY=sk-or-...")
    sys.exit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

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


def test_single_event(payload: dict) -> dict | None:
    """Send one event to the LLM, validate JSON output."""
    user_msg = f"Analyze this user activity record:\n{json.dumps([payload])}"

    print(f"\n--- Testing user_id: {payload['user_id']} ---")
    start = time.time()

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=1000,
        )
    except Exception as e:
        print(f"  API ERROR: {e}")
        return None

    elapsed = time.time() - start
    raw = response.choices[0].message.content.strip()

    print(f"  Response time: {elapsed:.2f}s")
    print(f"  Tokens used: {response.usage.total_tokens if response.usage else 'N/A'}")

    # try to parse JSON
    try:
        parsed = json.loads(raw)
        print(f"  JSON parse: ✅ VALID")
    except json.JSONDecodeError as e:
        print(f"  JSON parse: ❌ FAILED — {e}")
        print(f"  Raw output:\n{raw[:500]}")
        return None

    # validate structure
    if "results" not in parsed:
        print(f"  Structure: ❌ Missing 'results' key")
        print(f"  Got keys: {list(parsed.keys())}")
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
    print(f"  user_id: {result.get('user_id')}")
    print(f"  persistent: {json.dumps(result.get('persistent_updates', {}), indent=2)}")
    print(f"  episodic ({len(result.get('episodic_events', []))} events): ", end="")
    for evt in result.get("episodic_events", []):
        print(f"\n    - [{evt.get('event_type', '?')}] {evt.get('description', '?')}", end="")
    print()
    if result.get("inferred_preferences"):
        print(f"  preferences: {result['inferred_preferences']}")
    if result.get("contextual_signals"):
        print(f"  context: {result['contextual_signals']}")

    return parsed


def test_batch() -> dict | None:
    """Send all 3 events as a batch — this is how production works."""
    print("\n" + "=" * 60)
    print("BATCH TEST — 3 events in one call (production mode)")
    print("=" * 60)

    user_msg = f"Analyze these user activity records:\n{json.dumps(TEST_PAYLOADS)}"

    start = time.time()

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=2000,
        )
    except Exception as e:
        print(f"  API ERROR: {e}")
        return None

    elapsed = time.time() - start
    raw = response.choices[0].message.content.strip()

    print(f"  Response time: {elapsed:.2f}s")
    print(f"  Tokens used: {response.usage.total_tokens if response.usage else 'N/A'}")

    try:
        parsed = json.loads(raw)
        print(f"  JSON parse: ✅ VALID")
    except json.JSONDecodeError as e:
        print(f"  JSON parse: ❌ FAILED — {e}")
        print(f"  Raw output:\n{raw[:800]}")
        return None

    results = parsed.get("results", [])
    print(f"  Results count: {len(results)} (expected: 3)")

    for r in results:
        uid = r.get("user_id", "unknown")
        events = r.get("episodic_events", [])
        prefs = r.get("inferred_preferences", [])
        print(f"  [{uid}] → {len(events)} events, {len(prefs)} preferences")

    return parsed


if __name__ == "__main__":
    print("=" * 60)
    print(f"LLM Prompt Validation — OpenRouter")
    print(f"Model: {MODEL}")
    print("=" * 60)

    # individual tests
    all_passed = True
    for payload in TEST_PAYLOADS:
        result = test_single_event(payload)
        if result is None:
            all_passed = False

    # batch test
    batch_result = test_batch()
    if batch_result is None:
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED — Prompt is production-ready.")
        print("   The system prompt reliably produces valid JSON.")
        print("   Proceed to Phase 2 (infrastructure build).")
    else:
        print("❌ SOME TESTS FAILED — Prompt needs tuning.")
        print("   Check raw output above and adjust SYSTEM_PROMPT.")
        print("   Consider trying: mistralai/mistral-7b-instruct:free")
    print("=" * 60)
