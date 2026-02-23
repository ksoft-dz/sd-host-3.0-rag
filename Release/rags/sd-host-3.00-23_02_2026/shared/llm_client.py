#!/usr/bin/env python3
"""
LLM Client — Unified interface to Anthropic Claude API.

Wraps the Anthropic SDK with retry logic, rate limiting, and consistent error handling.
All LLM calls in the pipeline go through this module.
"""

import os
import sys
import time
import base64
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    import anthropic
except ImportError:
    print("ERROR: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)


class LLMClient:
    """Unified LLM client with retry and rate limiting."""
    
    def __init__(self, config: dict, model_override: str = None):
        """Initialize client from pipeline config.
        
        Args:
            config: Full spec_config.yaml dict
            model_override: Override model key (haiku/sonnet/opus) or direct model ID
        """
        self._client = anthropic.Anthropic()
        
        llm_config = config.get("llm", {})
        self._rate_limit_delay = llm_config.get("rate_limit_delay", 1.5)
        self._max_retries = llm_config.get("max_retries", 3)
        
        # Resolve model
        models = llm_config.get("models", {})
        if model_override:
            key = model_override.lower()
            self._model = models.get(key, model_override)
        else:
            default_key = llm_config.get("default_model", "sonnet")
            self._model = models.get(default_key, "claude-sonnet-4-5-20250929")
        
        self._last_call_time = 0
        self._total_calls = 0
        self._total_input_tokens = 0
        self._total_output_tokens = 0
    
    @property
    def model(self) -> str:
        return self._model
    
    @property
    def stats(self) -> dict:
        return {
            "total_calls": self._total_calls,
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "model": self._model
        }
    
    def _rate_limit(self):
        """Enforce rate limiting between calls."""
        elapsed = time.time() - self._last_call_time
        if elapsed < self._rate_limit_delay:
            time.sleep(self._rate_limit_delay - elapsed)
    
    def call(self, system: str, user: str, max_tokens: int = 4096,
             temperature: float = 0.0) -> str:
        """Make a text-only LLM call with retry.
        
        Args:
            system: System prompt
            user: User message
            max_tokens: Max output tokens
            temperature: Sampling temperature (0.0 = deterministic)
        
        Returns:
            Response text content
        """
        self._rate_limit()
        
        for attempt in range(self._max_retries):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}]
                )
                
                self._last_call_time = time.time()
                self._total_calls += 1
                self._total_input_tokens += response.usage.input_tokens
                self._total_output_tokens += response.usage.output_tokens
                
                return response.content[0].text
                
            except anthropic.RateLimitError:
                wait = (attempt + 1) * 5
                print(f"    Rate limited, waiting {wait}s (attempt {attempt + 1}/{self._max_retries})")
                time.sleep(wait)
            except anthropic.APIError as e:
                if attempt < self._max_retries - 1:
                    wait = (attempt + 1) * 3
                    print(f"    API error: {e}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise
            except (ConnectionError, TimeoutError, OSError) as e:
                if attempt < self._max_retries - 1:
                    wait = (attempt + 1) * 5
                    print(f"    Network error: {e}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        
        raise RuntimeError(f"LLM call failed after {self._max_retries} attempts")
    
    def call_with_image(self, system: str, user_text: str, image_data: bytes,
                        media_type: str = "image/png", max_tokens: int = 4096,
                        temperature: float = 0.0) -> str:
        """Make an LLM call with an image (vision).
        
        Args:
            system: System prompt
            user_text: Text prompt to accompany image
            image_data: Raw image bytes
            media_type: MIME type (image/png, image/jpeg)
            max_tokens: Max output tokens
            temperature: Sampling temperature
        
        Returns:
            Response text content
        """
        self._rate_limit()
        
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_b64
                    }
                },
                {
                    "type": "text",
                    "text": user_text
                }
            ]
        }]
        
        for attempt in range(self._max_retries):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=messages
                )
                
                self._last_call_time = time.time()
                self._total_calls += 1
                self._total_input_tokens += response.usage.input_tokens
                self._total_output_tokens += response.usage.output_tokens
                
                return response.content[0].text
                
            except anthropic.RateLimitError:
                wait = (attempt + 1) * 5
                print(f"    Rate limited, waiting {wait}s (attempt {attempt + 1}/{self._max_retries})")
                time.sleep(wait)
            except anthropic.APIError as e:
                if attempt < self._max_retries - 1:
                    wait = (attempt + 1) * 3
                    print(f"    API error: {e}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise
            except (ConnectionError, TimeoutError, OSError) as e:
                if attempt < self._max_retries - 1:
                    wait = (attempt + 1) * 5
                    print(f"    Network error: {e}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise
        
        raise RuntimeError(f"LLM vision call failed after {self._max_retries} attempts")
