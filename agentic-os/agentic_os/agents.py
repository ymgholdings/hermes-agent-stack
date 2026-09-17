"""Agent routing with OpenRouter direct API access."""

import os
import random
import time
from typing import Optional

import redis
from openai import OpenAI
from openai import OpenAIError

from .config import config
from .model_registry import AgentRole, get_model_for_role


class ModelRouter:
    """Routes agent requests to appropriate models via OpenRouter API."""

    def __init__(self):
        # Call OpenRouter directly (bypassing LiteLLM)
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY", config.openrouter_api_key),
        )
        self.redis_client = redis.from_url(config.redis_url)

    def call_agent(
        self,
        role: AgentRole,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Call an agent with automatic rate-limit handling and fallback.

        Args:
            role: Agent role to route to
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Agent response text

        Raises:
            OpenAIError: If all retries and fallbacks exhausted
        """
        # Get primary model for this role (attempt=0)
        model = get_model_for_role(role, attempt=0)
        return self._call_with_retry(role, model, prompt, system_prompt, temperature, max_tokens, retry_count=0)

    def _call_with_retry(
        self,
        role: AgentRole,
        model: str,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        retry_count: int = 0,
    ) -> str:
        """Call OpenRouter with role-based fallback and retry logic.

        Fallback strategy:
        1. On 429/502/503/529: retry with exponential backoff
        2. On None content or persistent errors: try next model in role's fallback chain
        3. Exhausted all fallbacks: raise error

        Args:
            role: Agent role (for fallback chain lookup)
            model: OpenRouter model ID to call
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            retry_count: Current retry attempt (maps to fallback chain index)

        Returns:
            Model response content

        Raises:
            OpenAIError: If all retries and fallbacks exhausted
        """
        backoff_key = f"ratelimit:{model}:backoff"

        # Check if we're in backoff period
        if self.redis_client.exists(backoff_key):
            time.sleep(3)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Extract content with defensive checks
            if not response.choices:
                raise OpenAIError(f"Model {model} returned no choices in response")

            content = response.choices[0].message.content

            if content is None:
                # Check if there's a refusal or other issue
                finish_reason = response.choices[0].finish_reason
                raise OpenAIError(
                    f"Model {model} returned None content (finish_reason: {finish_reason}). "
                    f"This may indicate content filtering, refusal, or API issue."
                )

            return content

        except OpenAIError as e:
            error_str = str(e)

            # Determine if we should try fallback model
            should_fallback = (
                "returned None content" in error_str
                or "429" in error_str
                or "rate_limit" in error_str.lower()
                or "502" in error_str
                or "503" in error_str
                or "529" in error_str
            )

            if should_fallback:
                # Try next model in the fallback chain
                try:
                    next_model = get_model_for_role(role, attempt=retry_count + 1)

                    # Exponential backoff with jitter
                    base_delay = 2.0  # 2 seconds base
                    backoff = base_delay * (2 ** retry_count)  # 2, 4, 8, 16...
                    jitter = random.uniform(0, 1.0)  # 0-1 second random jitter
                    wait_time = min(backoff + jitter, 30.0)  # Cap at 30 seconds

                    # Set Redis backoff marker if rate limit
                    if "429" in error_str or "rate_limit" in error_str.lower():
                        self.redis_client.setex(backoff_key, int(wait_time), "1")

                    time.sleep(wait_time)

                    return self._call_with_retry(
                        role,
                        next_model,
                        prompt,
                        system_prompt,
                        temperature,
                        max_tokens,
                        retry_count + 1,
                    )
                except (IndexError, ValueError):
                    # Exhausted all fallbacks - raise original error
                    raise e

            # Non-retriable error: propagate immediately
            raise


# Global router instance
router = ModelRouter()
