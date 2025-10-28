"""
Local LLM Handler
Handles communication with local LLM models (Ollama, LlamaCpp, etc.)
"""

import requests
import time
from typing import List, Dict, Optional
from pathlib import Path

from config.settings import (
    LOCAL_MODEL_URL,
    LOCAL_MODEL_NAME,
    LOCAL_MODEL_MAX_TOKENS,
    LOCAL_MODEL_TEMPERATURE,
    LOCAL_MODEL_TIMEOUT,
    LOCAL_VISION_CAPABLE
)
from utils.logger import get_logger
from utils.exceptions import ClaudeAPIError, RateLimitError
from utils.image_utils import image_to_base64

logger = get_logger(__name__)


def get_available_models(model_url: str = LOCAL_MODEL_URL) -> List[Dict]:
    """
    Get list of available models from Ollama server

    Args:
        model_url: URL of Ollama server

    Returns:
        List of model dictionaries with name, size, and modified date
    """
    try:
        response = requests.get(
            f"{model_url.rstrip('/')}/api/tags",
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            logger.info(f"Found {len(models)} available models")
            return models
        else:
            logger.warning(f"Failed to get models: status {response.status_code}")
            return []

    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not connect to Ollama server: {str(e)}")
        return []


class LocalLLMHandler:
    """
    Handler for local LLM models
    Supports Ollama API and compatible servers
    """

    def __init__(
        self,
        model_url: str = LOCAL_MODEL_URL,
        model_name: str = LOCAL_MODEL_NAME
    ):
        """Initialize local LLM handler"""
        self.model_url = model_url.rstrip('/')
        self.model_name = model_name
        self.max_tokens = LOCAL_MODEL_MAX_TOKENS
        self.temperature = LOCAL_MODEL_TEMPERATURE
        self.timeout = LOCAL_MODEL_TIMEOUT
        self.vision_capable = LOCAL_VISION_CAPABLE

        logger.info(f"Local LLM handler initialized: {model_name} at {model_url}")

        # Check if server is available
        self._check_server_availability()

    def _check_server_availability(self):
        """Check if the local LLM server is running and model is available"""
        try:
            response = requests.get(
                f"{self.model_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                logger.info(f"Local LLM server available. Models: {model_names}")

                # Check if our specific model is available
                model_found = False
                for name in model_names:
                    if self.model_name == name or self.model_name in name:
                        model_found = True
                        break

                if not model_found:
                    error_msg = (
                        f"Model '{self.model_name}' not found on Ollama server. "
                        f"Available models: {', '.join(model_names) if model_names else 'none'}. "
                        f"Install it with: ollama pull {self.model_name}"
                    )
                    logger.error(error_msg)
                    raise ClaudeAPIError(error_msg)
            else:
                logger.warning(f"Local LLM server returned status {response.status_code}")

        except ClaudeAPIError:
            # Re-raise our custom errors
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Local LLM server not available at {self.model_url}: {str(e)}")
            raise ClaudeAPIError(
                f"Cannot connect to local LLM server at {self.model_url}. "
                f"Please ensure Ollama is running with: ollama serve\n"
                f"Error: {str(e)}"
            )

    def make_api_call(
        self,
        messages: List[Dict],
        system_prompt: str,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Make API call to local LLM

        Args:
            messages: List of message dictionaries
            system_prompt: System prompt for the model
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        try:
            max_tokens = max_tokens or self.max_tokens

            # Convert messages to Ollama format
            prompt = self._format_prompt(messages, system_prompt)

            logger.debug(f"Making local LLM API call to {self.model_name}")

            # Prepare request payload
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": max_tokens
                }
            }

            # Make request to local server
            response = requests.post(
                f"{self.model_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')

                # Log token usage if available
                if 'eval_count' in result:
                    logger.info(f"Local LLM tokens generated: {result['eval_count']}")

                # Clean up reasoning model tags (e.g., <think> tags from deepseek-r1)
                # These are internal reasoning and should be removed for cleaner output
                import re
                # Remove complete think blocks
                generated_text = re.sub(r'<think>.*?</think>', '', generated_text, flags=re.DOTALL)
                generated_text = re.sub(r'<thinking>.*?</thinking>', '', generated_text, flags=re.DOTALL)
                # Remove orphaned opening/closing tags
                generated_text = re.sub(r'</?think>', '', generated_text)
                generated_text = re.sub(r'</?thinking>', '', generated_text)
                generated_text = generated_text.strip()

                return generated_text
            else:
                error_msg = f"Local LLM API returned status {response.status_code}"
                logger.error(error_msg)
                raise ClaudeAPIError(error_msg)

        except requests.exceptions.Timeout:
            logger.error("Local LLM request timed out")
            raise ClaudeAPIError(
                f"Local LLM request timed out after {self.timeout} seconds. "
                "Try a shorter prompt or increase timeout."
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Local LLM request failed: {str(e)}")
            raise ClaudeAPIError(f"Local LLM request failed: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error in local LLM call: {str(e)}")
            raise ClaudeAPIError(f"Unexpected error: {str(e)}")

    def _format_prompt(self, messages: List[Dict], system_prompt: str) -> str:
        """
        Format messages into a single prompt for local LLM

        Args:
            messages: List of message dictionaries
            system_prompt: System prompt

        Returns:
            Formatted prompt string
        """
        # Start with system prompt
        prompt = f"<|system|>\n{system_prompt}\n\n"

        # Add messages
        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')

            # Handle different content types
            if isinstance(content, str):
                prompt += f"<|{role}|>\n{content}\n\n"
            elif isinstance(content, list):
                # Handle multimodal content (text + images)
                text_parts = []
                for item in content:
                    if item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                    elif item.get('type') == 'image':
                        # Local models without vision just skip images
                        if not self.vision_capable:
                            text_parts.append("[Image content not available - local model doesn't support vision]")
                        else:
                            # For vision-capable local models (future support)
                            text_parts.append("[Image analysis would go here]")

                combined_text = '\n'.join(text_parts)
                prompt += f"<|{role}|>\n{combined_text}\n\n"

        # Add assistant prompt to encourage response
        prompt += "<|assistant|>\n"

        return prompt

    def supports_vision(self) -> bool:
        """Check if the local model supports vision"""
        return self.vision_capable

    def get_model_info(self) -> Dict:
        """Get information about the local model"""
        try:
            response = requests.post(
                f"{self.model_url}/api/show",
                json={"name": self.model_name},
                timeout=5
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {}

        except Exception as e:
            logger.warning(f"Could not get model info: {str(e)}")
            return {}
