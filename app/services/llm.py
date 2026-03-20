"""
Zave LLM Behavioral Extraction Service
This service is the 'Cognitive Engine' of Zave. It uses advanced Large Language Models
to parse unstructured, messy user data into structured behavioral insights.
"""

import os
import json
import logging
import time
from typing import Optional, Dict, Any, List

from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

# --- SYSTEM PROMPT DEFINITION ---
# This is the instruction set that governs how the LLM interprets raw data.
# It forces the LLM to act as a structured data extractor rather than a chatbot.
SYSTEM_PROMPT = """
You are a behavioral analysis engine for an e-commerce platform.
Your task is to extract user preferences, persona traits, and intent from raw unstructured text/logs.

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
    """
    LLMService manages connections to the OpenRouter API and handles model fallbacks.
    It ensures that even if one AI model is down or rate-limited, Zave continues to function.
    """

    def __init__(self):
        # We use AsyncOpenAI for non-blocking network calls during processing
        self.client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/zave/memory-system",
                "X-Title": "Zave Memory System"
            }
        )

        # A ranked list of reliable free-tier models on OpenRouter.
        # This provides automatic redundancy for our background worker.
        self.models = [
            "meta-llama/llama-3.3-70b-instruct:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "qwen/qwen3-coder:free",
        ]

    async def extract_behavioral_data(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Takes a raw event from the Data Lake and transforms it into structured memory updates.
        """
        raw_payload = event_data.get("raw_payload", "")
        
        # We wrap the user's raw data in a specific analysis request
        prompt = (
            f"Analyze this raw unstructured event payload and extract behavioral updates:\n\n"
            f"RAW PAYLOAD:\n{raw_payload}"
        )
        
        # --- MODEL FALLBACK LOOP ---
        for model in self.models:
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,  # Low temperature = high deterministic accuracy
                    max_tokens=1000,
                    response_format={"type": "json_object"}
                )
                
                content = response.choices[0].message.content
                if not content:
                    continue
                
                # We attempt to parse the string content into a Python dictionary
                return json.loads(content)
                
            except Exception as e:
                logger.warning(f"Failed to call LLM model {model}: {e}")
                
                # Check for rate limits (HTTP 429) and apply a brief wait before trying the next model
                if "429" in str(e):
                    time.sleep(2) 
                continue
        
        logger.error("All LLM models failed for behavioral extraction")
        return None

# Singleton instance for high-efficiency reuse of the OpenAI client
llm_service = LLMService()
