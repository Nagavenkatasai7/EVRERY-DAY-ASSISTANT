"""
Universal Model Client for Resume Maker
Routes requests to Claude, Grok, or Local LLM based on MODEL_MODE
"""
import os
from dotenv import load_dotenv

load_dotenv()


class UniversalModelClient:
    """
    Universal client that routes to Claude, Grok, or Local LLM
    Provides a unified interface for resume generation components
    """

    def __init__(self, model_mode=None):
        """
        Initialize universal model client

        Args:
            model_mode: 'api' (Claude), 'grok' (xAI), 'local' (Ollama), or None (auto-detect from env)
        """
        self.model_mode = model_mode or os.getenv('MODEL_MODE', 'api').lower()
        self.client = None
        self.grok_handler = None
        self.local_handler = None
        self.model_name = None

        # Initialize appropriate client
        if self.model_mode == 'api':
            self._init_claude()
        elif self.model_mode == 'grok':
            self._init_grok()
        elif self.model_mode == 'local':
            self._init_local()
        else:
            raise ValueError(f"Invalid MODEL_MODE: {self.model_mode}. Must be 'api', 'grok', or 'local'")

    def _init_claude(self):
        """Initialize Claude API client"""
        import anthropic
        api_key = os.getenv('ANTHROPIC_API_KEY')

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY required when MODEL_MODE='api'")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model_name = "claude-sonnet-4-5-20250929"
        print(f"✓ Resume Model Client: Using Claude API ({self.model_name})")

    def _init_grok(self):
        """Initialize Grok API handler"""
        from src.grok_handler import GrokHandler

        grok_key = os.getenv('GROK_API_KEY') or os.getenv('XAI_API')
        if not grok_key:
            raise ValueError("GROK_API_KEY or XAI_API required when MODEL_MODE='grok'")

        self.grok_handler = GrokHandler()
        self.model_name = os.getenv('GROK_MODEL', 'grok-4-fast-reasoning')
        print(f"✓ Resume Model Client: Using Grok API ({self.model_name})")

    def _init_local(self):
        """Initialize Local LLM handler"""
        from src.local_llm_handler import LocalLLMHandler

        model_name = os.getenv('LOCAL_MODEL_NAME', 'llama3.1:latest')
        self.local_handler = LocalLLMHandler(model_name=model_name)
        self.model_name = model_name
        print(f"✓ Resume Model Client: Using Local LLM ({self.model_name})")

    def generate(self, prompt, max_tokens=4000, temperature=0.7):
        """
        Generate response using configured model

        Args:
            prompt: User prompt text
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Generated text response
        """
        if self.model_mode == 'api':
            return self._generate_claude(prompt, max_tokens, temperature)
        elif self.model_mode == 'grok':
            return self._generate_grok(prompt, max_tokens, temperature)
        elif self.model_mode == 'local':
            return self._generate_local(prompt, max_tokens, temperature)

    def _generate_claude(self, prompt, max_tokens, temperature):
        """Generate with Claude API"""
        try:
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")

    def _generate_grok(self, prompt, max_tokens, temperature):
        """Generate with Grok API"""
        try:
            grok_max_tokens = int(os.getenv('GROK_MAX_TOKENS', '8192'))
            grok_temperature = float(os.getenv('GROK_TEMPERATURE', '0.7'))

            # Override with provided values
            max_tokens = min(max_tokens, grok_max_tokens)

            response = self.grok_handler.generate_response(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature or grok_temperature
            )
            return response
        except Exception as e:
            raise Exception(f"Grok API error: {str(e)}")

    def _generate_local(self, prompt, max_tokens, temperature):
        """Generate with Local LLM"""
        try:
            response = self.local_handler.make_api_call(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert resume writer and job description analyst.",
                max_tokens=max_tokens
            )
            return response
        except Exception as e:
            raise Exception(f"Local LLM error: {str(e)}")

    def get_model_name(self):
        """Get the name of the currently active model"""
        if self.model_mode == 'api':
            return f'Claude ({self.model_name})'
        elif self.model_mode == 'grok':
            return f'Grok ({self.model_name})'
        elif self.model_mode == 'local':
            return f'Local LLM ({self.model_name})'
        else:
            return 'Unknown'


def main():
    """Test universal model client"""
    print("Testing Universal Model Client...\n")

    # Test with auto-detection
    client = UniversalModelClient()
    print(f"Active Model: {client.get_model_name()}\n")

    # Test generation
    test_prompt = "What are the key components of an ATS-optimized resume?"

    try:
        response = client.generate(test_prompt, max_tokens=200)
        print("✓ Generation successful")
        print(f"Response preview: {response[:200]}...")
    except Exception as e:
        print(f"✗ Generation failed: {e}")


if __name__ == "__main__":
    main()
