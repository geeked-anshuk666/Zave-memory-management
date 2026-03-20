import os
import json
import logging
import time
from typing import Optional, Dict, Any, List
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

# System prompt optimized for structured extraction from e-commerce events
SYSTEM_PROMPT = """
You are a behavioral analysis engine for an e-commerce platform.
Your task is to extract user preferences, persona traits, and intent from raw activity events.

STRICT RULES:
1. Return ONLY valid JSON. 
2. No preamble, no explanation, no markdown blocks.
3. If an event has no clear signal for a field, use null.
4. Time of day must be one of: [morning, afternoon, evening, night].

Output Schema:
{
  "user_id": "string",
  "persistent_updates": {
    "preferred_categories": ["string"],
    "price_sensitivity": "low" | "medium" | "high" | null,
    "last_active_time_of_day": "string" | null
  },
  "episodic_events": [
    {
      "event_type": "string",
      "summary": "string",
      "sentiment": "positive" | "neutral" | "negative",
      "timestamp": "ISO8601 string"
    }
  ],
  "inferred_preferences": ["string"]
}
"""

class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/zave/memory-system",
                "X-Title": "Zave Memory System"
            }
        )
        self.models = [
            "meta-llama/llama-3.3-70b-instruct:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "qwen/qwen3-coder:free",
        ]

    async def extract_behavioral_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Calls LLM to extract behavioral data from a single event.
        Includes ranked fallback for reliable free-tier usage.
        """
        prompt = f"Analyze this event and provide behavioral updates:\n{json.dumps(event_data, indent=2)}"
        
        for model in self.models:
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=1000,
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                if not content:
                    continue
                
                return json.loads(content)
                
            except Exception as e:
                logger.warning(f"Failed to call LLM model {model}: {e}")
                if "429" in str(e):
                    time.sleep(2) # Backoff for rate limit
                continue
        
        logger.error("All LLM models failed for behavioral extraction")
        return None

llm_service = LLMService()
