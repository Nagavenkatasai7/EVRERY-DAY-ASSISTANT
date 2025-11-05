"""
Model Router
Intelligently routes tasks between Claude Opus 4 (expensive, powerful) and Claude Sonnet 4 (cheaper, efficient)
for cost-optimized multi-agent architecture
"""

import time
from typing import List, Dict, Optional
import anthropic
from anthropic import APIError, APIConnectionError, RateLimitError as AnthropicRateLimitError
import tiktoken

from config.settings import (
    ANTHROPIC_API_KEY,
    CLAUDE_TEMPERATURE,
    CLAUDE_REQUEST_TIMEOUT,
    CLAUDE_MAX_RETRIES,
    CLAUDE_RETRY_DELAY,
    ENABLE_PROMPT_CACHING
)
from utils.logger import get_logger
from utils.exceptions import ClaudeAPIError, RateLimitError, AuthenticationError

logger = get_logger(__name__)

# Safety limits to prevent excessive API costs
MAX_CONTEXT_TOKENS = 180000  # Claude's actual limit is 200K, use 180K for safety
MAX_OUTPUT_TOKENS = 16000  # Maximum output tokens per request
COST_WARNING_THRESHOLD = 5.0  # Warn if estimated cost exceeds $5 per request
MAX_MESSAGE_LENGTH = 500000  # Maximum characters per message (approximate)


class ModelRouter:
    """
    Routes tasks to appropriate Claude model for cost optimization:
    - Opus 4: Planning, synthesis, high-level reasoning (expensive)
    - Sonnet 4: Execution, analysis, information gathering (5× cheaper)
    """

    # Model specifications
    OPUS_MODEL = "claude-opus-4-20250514"
    SONNET_MODEL = "claude-sonnet-4-5-20250929"

    # Pricing per 1M tokens (input/output)
    PRICING = {
        "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
        "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
        "cache_read": 0.30  # 90% discount on cached content
    }

    # Task type to model mapping
    TASK_ROUTING = {
        "planning": OPUS_MODEL,  # High-level research planning
        "synthesis": OPUS_MODEL,  # Combining findings from multiple sources
        "verification": OPUS_MODEL,  # Citation and fact checking
        "execution": SONNET_MODEL,  # Information gathering and analysis
        "analysis": SONNET_MODEL,  # Document analysis
        "retrieval": SONNET_MODEL,  # Context retrieval and processing
    }

    def __init__(self):
        """Initialize model router with Anthropic client and token counter"""
        try:
            self.client = anthropic.Anthropic(
                api_key=ANTHROPIC_API_KEY,
                timeout=CLAUDE_REQUEST_TIMEOUT
            )

            # Initialize tokenizer for token counting
            try:
                self.tokenizer = tiktoken.encoding_for_model("gpt-4")  # Similar tokenization
                logger.info("✓ Token counter initialized")
            except Exception as e:
                logger.warning(f"Token counter initialization failed: {str(e)}, using character approximation")
                self.tokenizer = None

            logger.info("🎯 Model Router initialized (Opus 4 + Sonnet 4)")
            logger.info(f"   💰 Opus: ${self.PRICING[self.OPUS_MODEL]['input']}/1M input tokens")
            logger.info(f"   ⚡ Sonnet: ${self.PRICING[self.SONNET_MODEL]['input']}/1M input tokens (5× cheaper)")
            logger.info(f"   🛡️  Safety limits: {MAX_CONTEXT_TOKENS:,} context tokens max, ${COST_WARNING_THRESHOLD} cost threshold")

        except Exception as e:
            logger.error(f"Failed to initialize Model Router: {str(e)}")
            raise ClaudeAPIError(f"Router initialization failed: {str(e)}")

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        try:
            if self.tokenizer:
                return len(self.tokenizer.encode(text))
            else:
                # Fallback: approximate as chars/4
                return len(text) // 4
        except Exception as e:
            logger.warning(f"Token estimation failed: {str(e)}, using character approximation")
            return len(text) // 4

    def _validate_request(
        self,
        model: str,
        messages: List[Dict],
        system_prompt: str,
        max_tokens: int
    ) -> tuple[bool, Optional[str]]:
        """
        Validate request to prevent expensive failures

        Args:
            model: Model name
            messages: Message list
            system_prompt: System prompt
            max_tokens: Max output tokens

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Validate max_tokens
            if max_tokens > MAX_OUTPUT_TOKENS:
                return False, f"max_tokens ({max_tokens}) exceeds limit ({MAX_OUTPUT_TOKENS})"

            # Estimate input token count
            total_text = system_prompt + " " + " ".join(
                msg.get("content", "") for msg in messages if isinstance(msg.get("content"), str)
            )

            estimated_input_tokens = self._estimate_tokens(total_text)

            # Check context length
            if estimated_input_tokens > MAX_CONTEXT_TOKENS:
                return False, (
                    f"Estimated input tokens ({estimated_input_tokens:,}) exceeds "
                    f"context limit ({MAX_CONTEXT_TOKENS:,}). "
                    f"Consider reducing context size."
                )

            # Estimate cost and warn if high
            pricing = self.PRICING.get(model, self.PRICING[self.SONNET_MODEL])
            estimated_cost = (
                (estimated_input_tokens / 1_000_000) * pricing["input"] +
                (max_tokens / 1_000_000) * pricing["output"]
            )

            if estimated_cost > COST_WARNING_THRESHOLD:
                logger.warning(
                    f"⚠️  HIGH COST WARNING: Estimated ${estimated_cost:.2f} for this request "
                    f"(input: {estimated_input_tokens:,} tokens, output: {max_tokens:,} tokens)"
                )

            logger.debug(f"Request validated: ~{estimated_input_tokens:,} input tokens, est. cost ${estimated_cost:.4f}")
            return True, None

        except Exception as e:
            logger.error(f"Request validation failed: {str(e)}")
            return False, f"Validation error: {str(e)}"

    def route_task(
        self,
        task_type: str,
        messages: List[Dict],
        system_prompt: str,
        max_tokens: int = 8000,
        use_cache: bool = True
    ) -> Dict:
        """
        Route task to appropriate model with validation and safety checks

        Args:
            task_type: Type of task (planning, synthesis, execution, etc.)
            messages: List of message dictionaries
            system_prompt: System prompt text
            max_tokens: Maximum tokens for response
            use_cache: Whether to use prompt caching (default: True)

        Returns:
            Dictionary with response text, model used, and cost information

        Raises:
            ClaudeAPIError: If validation fails or API call errors
        """
        # Determine which model to use
        model = self.TASK_ROUTING.get(task_type, self.SONNET_MODEL)

        # Validate request before making expensive API call
        is_valid, error_msg = self._validate_request(model, messages, system_prompt, max_tokens)
        if not is_valid:
            logger.error(f"❌ Request validation failed: {error_msg}")
            raise ClaudeAPIError(f"Request validation failed: {error_msg}")

        # Log routing decision
        model_name = "Opus 4" if model == self.OPUS_MODEL else "Sonnet 4"
        emoji = "🧠" if model == self.OPUS_MODEL else "⚡"
        logger.info(f"{emoji} Routing '{task_type}' task to {model_name}")

        # Make API call
        return self._make_api_call(
            model=model,
            messages=messages,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            use_cache=use_cache
        )

    def _make_api_call(
        self,
        model: str,
        messages: List[Dict],
        system_prompt: str,
        max_tokens: int,
        use_cache: bool
    ) -> Dict:
        """Make API call with retry logic and prompt caching"""

        for attempt in range(CLAUDE_MAX_RETRIES):
            try:
                logger.debug(f"API call attempt {attempt + 1}/{CLAUDE_MAX_RETRIES} with {model}")

                # Build system message with prompt caching if enabled
                if use_cache and ENABLE_PROMPT_CACHING:
                    system_message = [{
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}
                    }]
                else:
                    system_message = system_prompt

                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=CLAUDE_TEMPERATURE,
                    system=system_message,
                    messages=messages
                )

                if response.content and len(response.content) > 0:
                    result_text = response.content[0].text

                    # Calculate cost
                    cost_info = self._calculate_cost(response, model)

                    # Log usage and cost
                    logger.info(
                        f"✅ API call successful - "
                        f"Input: {cost_info['input_tokens']}, "
                        f"Output: {cost_info['output_tokens']}, "
                        f"Cost: ${cost_info['total_cost']:.4f}"
                    )

                    # Log cache savings if applicable
                    if cost_info['cache_read_tokens'] > 0:
                        logger.info(
                            f"💰 Cache savings: {cost_info['cache_read_tokens']} tokens "
                            f"(${cost_info['cache_savings']:.4f} saved)"
                        )

                    return {
                        "response": result_text,
                        "model": model,
                        "cost_info": cost_info
                    }

                raise ClaudeAPIError("Empty response from Claude API")

            except AnthropicRateLimitError as e:
                logger.warning(f"Rate limit exceeded (attempt {attempt + 1})")
                if attempt < CLAUDE_MAX_RETRIES - 1:
                    wait_time = CLAUDE_RETRY_DELAY * (attempt + 1)
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    raise RateLimitError(f"Rate limit exceeded after {CLAUDE_MAX_RETRIES} attempts")

            except APIConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt + 1}): {str(e)}")
                if attempt < CLAUDE_MAX_RETRIES - 1:
                    time.sleep(CLAUDE_RETRY_DELAY)
                else:
                    raise ClaudeAPIError(f"Connection failed after {CLAUDE_MAX_RETRIES} attempts: {str(e)}")

            except anthropic.AuthenticationError as e:
                logger.error(f"Authentication error: {str(e)}")
                raise AuthenticationError(f"Invalid API key: {str(e)}")

            except APIError as e:
                logger.error(f"Claude API error: {str(e)}")
                if attempt < CLAUDE_MAX_RETRIES - 1:
                    time.sleep(CLAUDE_RETRY_DELAY)
                else:
                    raise ClaudeAPIError(f"API error after {CLAUDE_MAX_RETRIES} attempts: {str(e)}")

            except Exception as e:
                logger.error(f"Unexpected error in API call: {str(e)}")
                raise ClaudeAPIError(f"Unexpected error: {str(e)}")

        raise ClaudeAPIError("Max retries exceeded")

    def _calculate_cost(self, response, model: str) -> Dict:
        """Calculate cost from API response"""

        usage = response.usage
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
        cache_read_tokens = getattr(usage, 'cache_read_input_tokens', 0)
        cache_creation_tokens = getattr(usage, 'cache_creation_input_tokens', 0)

        # Get pricing for model
        pricing = self.PRICING[model]

        # Calculate costs
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        cache_read_cost = (cache_read_tokens / 1_000_000) * self.PRICING["cache_read"]

        # Cache savings (cache reads cost 90% less than regular input)
        cache_savings = (cache_read_tokens / 1_000_000) * (pricing["input"] - self.PRICING["cache_read"])

        total_cost = input_cost + output_cost + cache_read_cost

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_creation_tokens": cache_creation_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "cache_read_cost": cache_read_cost,
            "cache_savings": cache_savings,
            "total_cost": total_cost,
            "model": model
        }

    def estimate_cost(
        self,
        task_type: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
        use_cache: bool = True,
        cache_hit_rate: float = 0.7
    ) -> Dict:
        """
        Estimate cost for a task before execution

        Args:
            task_type: Type of task
            estimated_input_tokens: Estimated input tokens
            estimated_output_tokens: Estimated output tokens
            use_cache: Whether caching will be used
            cache_hit_rate: Expected cache hit rate (default: 70%)

        Returns:
            Dictionary with cost estimates
        """
        model = self.TASK_ROUTING.get(task_type, self.SONNET_MODEL)
        pricing = self.PRICING[model]

        # Calculate with and without caching
        base_input_cost = (estimated_input_tokens / 1_000_000) * pricing["input"]
        output_cost = (estimated_output_tokens / 1_000_000) * pricing["output"]

        if use_cache and ENABLE_PROMPT_CACHING:
            # With caching: some tokens read from cache (90% cheaper)
            cached_tokens = int(estimated_input_tokens * cache_hit_rate)
            non_cached_tokens = estimated_input_tokens - cached_tokens

            cached_input_cost = (cached_tokens / 1_000_000) * self.PRICING["cache_read"]
            non_cached_input_cost = (non_cached_tokens / 1_000_000) * pricing["input"]
            total_input_cost = cached_input_cost + non_cached_input_cost

            savings = base_input_cost - total_input_cost
        else:
            total_input_cost = base_input_cost
            savings = 0.0

        total_cost = total_input_cost + output_cost

        return {
            "model": model,
            "estimated_cost": total_cost,
            "input_cost": total_input_cost,
            "output_cost": output_cost,
            "cache_savings": savings,
            "cost_without_cache": base_input_cost + output_cost
        }
