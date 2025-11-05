"""
Grok API Handler - xAI Grok 4 Fast Integration
Handles communication with xAI's Grok 4 Fast reasoning models
"""

import time
import requests
from typing import List, Dict, Optional
from config.settings import (
    GROK_API_KEY,
    GROK_MODEL,
    GROK_MAX_TOKENS,
    GROK_TEMPERATURE,
    GROK_REQUEST_TIMEOUT,
    GROK_MAX_RETRIES,
    GROK_RETRY_DELAY,
)
from utils.logger import get_logger
from utils.exceptions import ClaudeAPIError, RateLimitError, AuthenticationError

logger = get_logger(__name__)


class GrokHandler:
    """Handler for xAI Grok 4 Fast API"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Grok handler

        Args:
            api_key: xAI API key (defaults to settings)
        """
        self.api_key = api_key or GROK_API_KEY
        self.base_url = "https://api.x.ai/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        logger.info("Initialized Grok API handler")

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = GROK_MAX_TOKENS,
        temperature: float = GROK_TEMPERATURE,
        model: str = GROK_MODEL,
        stream: bool = False
    ) -> str:
        """Generate response using Grok API

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            model: Grok model to use
            stream: Whether to stream the response

        Returns:
            Generated text response

        Raises:
            AuthenticationError: If API key is invalid
            RateLimitError: If rate limit is exceeded
            ClaudeAPIError: For other API errors
        """
        endpoint = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }

        for attempt in range(GROK_MAX_RETRIES):
            try:
                logger.info(f"Sending request to Grok API (attempt {attempt + 1}/{GROK_MAX_RETRIES})")
                logger.debug(f"Model: {model}, Messages: {len(messages)}, Max tokens: {max_tokens}")

                response = requests.post(
                    endpoint,
                    headers=self.headers,
                    json=payload,
                    timeout=GROK_REQUEST_TIMEOUT
                )

                # Handle different status codes
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']

                    # Log usage statistics if available
                    if 'usage' in result:
                        usage = result['usage']
                        logger.info(f"Grok API usage - Input: {usage.get('prompt_tokens', 0)}, "
                                  f"Output: {usage.get('completion_tokens', 0)}, "
                                  f"Total: {usage.get('total_tokens', 0)}")

                    return content

                elif response.status_code == 401:
                    raise AuthenticationError("Invalid xAI API key")

                elif response.status_code == 429:
                    logger.warning("Rate limit exceeded, retrying...")
                    if attempt < GROK_MAX_RETRIES - 1:
                        time.sleep(GROK_RETRY_DELAY * (attempt + 1))
                        continue
                    raise RateLimitError("Grok API rate limit exceeded")

                elif response.status_code >= 500:
                    logger.warning(f"Server error {response.status_code}, retrying...")
                    if attempt < GROK_MAX_RETRIES - 1:
                        time.sleep(GROK_RETRY_DELAY)
                        continue
                    raise ClaudeAPIError(f"Grok API server error: {response.status_code}")

                else:
                    error_msg = response.json().get('error', {}).get('message', 'Unknown error')
                    raise ClaudeAPIError(f"Grok API error {response.status_code}: {error_msg}")

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1})")
                if attempt < GROK_MAX_RETRIES - 1:
                    time.sleep(GROK_RETRY_DELAY)
                    continue
                raise ClaudeAPIError("Grok API request timeout")

            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error: {str(e)}")
                if attempt < GROK_MAX_RETRIES - 1:
                    time.sleep(GROK_RETRY_DELAY)
                    continue
                raise ClaudeAPIError(f"Failed to connect to Grok API: {str(e)}")

            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                raise ClaudeAPIError(f"Grok API error: {str(e)}")

        raise ClaudeAPIError("Max retries exceeded")

    def analyze_with_grok(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = GROK_MAX_TOKENS,
        temperature: float = GROK_TEMPERATURE
    ) -> str:
        """Analyze content using Grok with system and user prompts

        Args:
            system_prompt: System instruction
            user_prompt: User query/content
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Grok's analysis response
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self.generate_response(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )

    def synthesize_research(
        self,
        retrieved_chunks: List[Dict],
        query: str,
        system_prompt: str
    ) -> str:
        """Synthesize research findings using Grok

        Args:
            retrieved_chunks: List of document chunks with content and metadata
            query: Research query
            system_prompt: System instruction for synthesis

        Returns:
            Synthesized research notes
        """
        # Format the retrieved content
        context = "\n\n".join([
            f"**Document**: {chunk['metadata'].get('source', 'Unknown')}\n"
            f"**Page**: {chunk['metadata'].get('page', 'N/A')}\n"
            f"**Content**:\n{chunk['content']}"
            for chunk in retrieved_chunks
        ])

        user_prompt = f"""Research Query: {query}

Retrieved Research Content:
{context}

Please synthesize this information into comprehensive research notes following the system instructions."""

        return self.analyze_with_grok(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=GROK_MAX_TOKENS
        )
