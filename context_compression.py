"""
context_compression.py - Context Compression Layer for CloudBrain
Handles summarization and context window management for long-running tasks.
"""

import json
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from config import config
from utils.logger import logger
from utils.resilience import retry_with_backoff

COMPRESSION_PROMPT = """You are an expert at summarizing long conversations and context windows.

Your task is to extract the MOST IMPORTANT information from the following conversation history, discarding redundant or low-signal content.

RULES FOR COMPRESSION:
1. Keep all factual claims and their sources
2. Remove repeated explanations
3. Preserve user preferences and constraints
4. Keep all numerical data and metrics
5. Remove pleasantries and meta-commentary
6. Target output length: 40-60% of original

CONVERSATION HISTORY:
{history}

COMPRESSED SUMMARY:
(Provide a concise summary that retains all critical information)"""

CONTEXT_HIERARCHY_PROMPT = """You are analyzing a request to identify what information is CRITICAL for solving it.

Categorize the following context into tiers:
- TIER 1 (CRITICAL): Must include in next request
- TIER 2 (IMPORTANT): Should include if space allows
- TIER 3 (NICE-TO-HAVE): Include only if there's capacity

CONTEXT:
{context}

ORIGINAL REQUEST:
{request}

Return JSON:
{{
  "tier_1": ["item1", "item2", ...],
  "tier_2": ["item3", "item4", ...],
  "tier_3": ["item5", ...]
}}"""


class ContextCompressor:
    """Handles compression and prioritization of context for long-running tasks."""

    def __init__(self):
        self.max_context_tokens = 8000  # Reserve tokens for response
        self.tier_weights = {"tier_1": 1.0, "tier_2": 0.6, "tier_3": 0.2}

    @retry_with_backoff(retries=2, backoff_factor=1.5)
    def call_compression_llm(self, prompt: str) -> str:
        """Call Cloud LLM for compression tasks (uses faster models)."""
        # Try OpenAI (faster model for compression)
        if config.OPENAI_API_KEY:
            try:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-3.5-turbo",  # Faster for compression
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1
                    },
                    timeout=20
                )
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content']
            except Exception as e:
                logger.warning(f"OpenAI compression failed: {e}")

        # Fallback to Gemini
        if config.GEMINI_API_KEY:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={config.GEMINI_API_KEY}"
                response = requests.post(
                    url,
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=20
                )
                response.raise_for_status()
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                logger.warning(f"Gemini compression failed: {e}")

        return ""

    def estimate_tokens(self, text: str) -> int:
        """Quick approximation: ~4 chars per token on average."""
        return len(text) // 4

    def compress_history(self, history: List[Dict[str, str]]) -> str:
        """Compress conversation history while preserving critical information."""
        if not history:
            return ""

        history_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history])
        
        # Check if compression is needed
        history_tokens = self.estimate_tokens(history_text)
        if history_tokens < 2000:
            logger.info(f"History within limits ({history_tokens} tokens). No compression needed.")
            return history_text

        logger.info(f"Compressing history from {history_tokens} tokens...")
        
        prompt = COMPRESSION_PROMPT.format(history=history_text)
        compressed = self.call_compression_llm(prompt)
        
        compressed_tokens = self.estimate_tokens(compressed)
        compression_ratio = (1 - compressed_tokens / history_tokens) * 100
        logger.info(f"Compression complete: {history_tokens} → {compressed_tokens} tokens ({compression_ratio:.1f}% reduction)")
        
        return compressed

    def prioritize_context(self, context: str, request: str) -> Dict[str, List[str]]:
        """Categorize context into tiers based on request relevance."""
        prompt = CONTEXT_HIERARCHY_PROMPT.format(context=context, request=request)
        result_text = self.call_compression_llm(prompt)
        
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
        except:
            logger.warning("Failed to parse tier categorization. Using fallback.")
        
        # Fallback: split by sentences and categorize naively
        sentences = context.split(". ")
        return {
            "tier_1": sentences[:len(sentences)//3],
            "tier_2": sentences[len(sentences)//3:2*len(sentences)//3],
            "tier_3": sentences[2*len(sentences)//3:]
        }

    def build_minimal_context(self, tiers: Dict[str, List[str]], budget_tokens: int = 4000) -> str:
        """Build context window respecting token budget."""
        context_parts = []
        current_tokens = 0

        # Add TIER 1 first (mandatory)
        for item in tiers.get("tier_1", []):
            item_tokens = self.estimate_tokens(item)
            if current_tokens + item_tokens < budget_tokens:
                context_parts.append(f"[CRITICAL] {item}")
                current_tokens += item_tokens

        # Add TIER 2 if space allows
        for item in tiers.get("tier_2", []):
            item_tokens = self.estimate_tokens(item)
            if current_tokens + item_tokens < budget_tokens * 0.7:
                context_parts.append(f"[IMPORTANT] {item}")
                current_tokens += item_tokens

        # Add TIER 3 if space allows
        for item in tiers.get("tier_3", []):
            item_tokens = self.estimate_tokens(item)
            if current_tokens + item_tokens < budget_tokens:
                context_parts.append(f"[OPTIONAL] {item}")
                current_tokens += item_tokens

        final_context = "\n".join(context_parts)
        logger.info(f"Built context window: {current_tokens}/{budget_tokens} tokens")
        
        return final_context

    def handle_context_overflow(self, history: List[Dict], current_request: str, max_tokens: int = 8000) -> Dict[str, Any]:
        """
        Main entry point: handles context overflow for long conversations.
        Returns optimized context suitable for Cloud Brain.
        """
        logger.info(f"Handling context overflow (target: {max_tokens} tokens)")

        # Step 1: Compress history
        compressed_history = self.compress_history(history)
        
        # Step 2: Prioritize what's critical
        tiers = self.prioritize_context(compressed_history, current_request)
        
        # Step 3: Build minimal context respecting token budget
        optimized_context = self.build_minimal_context(tiers, max_tokens)
        
        return {
            "optimized_context": optimized_context,
            "original_tokens": self.estimate_tokens(compressed_history),
            "optimized_tokens": self.estimate_tokens(optimized_context),
            "tiers": tiers,
            "timestamp": datetime.now().isoformat()
        }
