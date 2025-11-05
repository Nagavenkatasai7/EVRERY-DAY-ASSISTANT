"""
Unit tests for UniversalModelClient
Tests model routing between Claude, Grok, and Local LLM
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.resume_utils.model_client import UniversalModelClient


class TestUniversalModelClient:
    """Test suite for UniversalModelClient"""

    def test_init_with_claude_api_mode(self):
        """Test initialization with Claude API mode"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                client = UniversalModelClient(model_mode='api')

                assert client.model_mode == 'api'
                assert client.model_name == "claude-sonnet-4-5-20250929"
                assert client.grok_handler is None
                assert client.local_handler is None
                mock_anthropic.assert_called_once()

    def test_init_with_grok_mode(self):
        """Test initialization with Grok mode"""
        with patch.dict(os.environ, {'MODEL_MODE': 'grok', 'GROK_API_KEY': 'test_key'}):
            with patch('src.grok_handler.GrokHandler') as mock_grok:
                client = UniversalModelClient(model_mode='grok')

                assert client.model_mode == 'grok'
                assert client.client is None
                assert client.local_handler is None
                mock_grok.assert_called_once()

    def test_init_with_local_mode(self):
        """Test initialization with Local LLM mode"""
        with patch.dict(os.environ, {'MODEL_MODE': 'local', 'LOCAL_MODEL_NAME': 'llama3.1:latest'}):
            with patch('src.local_llm_handler.LocalLLMHandler') as mock_local:
                client = UniversalModelClient(model_mode='local')

                assert client.model_mode == 'local'
                assert client.client is None
                assert client.grok_handler is None
                mock_local.assert_called_once()

    def test_init_with_invalid_mode(self):
        """Test initialization with invalid mode raises ValueError"""
        with pytest.raises(ValueError, match="Invalid MODEL_MODE"):
            UniversalModelClient(model_mode='invalid')

    def test_init_without_api_key_for_claude(self):
        """Test initialization fails without API key for Claude"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api'}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY required"):
                UniversalModelClient(model_mode='api')

    def test_init_without_api_key_for_grok(self):
        """Test initialization fails without API key for Grok"""
        with patch.dict(os.environ, {'MODEL_MODE': 'grok'}, clear=True):
            with pytest.raises(ValueError, match="GROK_API_KEY or XAI_API required"):
                UniversalModelClient(model_mode='grok')

    def test_generate_with_claude(self):
        """Test text generation with Claude API"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                # Mock the API response
                mock_message = Mock()
                mock_content = Mock()
                mock_content.text = "Test response from Claude"
                mock_message.content = [mock_content]

                mock_client = Mock()
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                client = UniversalModelClient(model_mode='api')
                response = client.generate("Test prompt", max_tokens=100, temperature=0.7)

                assert response == "Test response from Claude"
                mock_client.messages.create.assert_called_once()

    def test_generate_with_grok(self):
        """Test text generation with Grok API"""
        with patch.dict(os.environ, {'MODEL_MODE': 'grok', 'GROK_API_KEY': 'test_key',
                                     'GROK_MAX_TOKENS': '8192', 'GROK_TEMPERATURE': '0.7'}):
            with patch('src.grok_handler.GrokHandler') as mock_grok_class:
                mock_grok = Mock()
                mock_grok.generate_response.return_value = "Test response from Grok"
                mock_grok_class.return_value = mock_grok

                client = UniversalModelClient(model_mode='grok')
                response = client.generate("Test prompt", max_tokens=100, temperature=0.7)

                assert response == "Test response from Grok"
                mock_grok.generate_response.assert_called_once()

    def test_generate_with_local_llm(self):
        """Test text generation with Local LLM"""
        with patch.dict(os.environ, {'MODEL_MODE': 'local', 'LOCAL_MODEL_NAME': 'llama3.1:latest'}):
            with patch('src.local_llm_handler.LocalLLMHandler') as mock_local_class:
                mock_local = Mock()
                mock_local.make_api_call.return_value = "Test response from Local LLM"
                mock_local.model_name = "llama3.1:latest"
                mock_local_class.return_value = mock_local

                client = UniversalModelClient(model_mode='local')
                response = client.generate("Test prompt", max_tokens=100, temperature=0.7)

                assert response == "Test response from Local LLM"
                mock_local.make_api_call.assert_called_once()

    def test_generate_handles_api_error(self):
        """Test that API errors are properly handled"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = Mock()
                mock_client.messages.create.side_effect = Exception("API Error")
                mock_anthropic.return_value = mock_client

                client = UniversalModelClient(model_mode='api')

                with pytest.raises(Exception, match="Claude API error"):
                    client.generate("Test prompt")

    def test_get_model_name_for_claude(self):
        """Test get_model_name returns correct name for Claude"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                client = UniversalModelClient(model_mode='api')
                assert "Claude" in client.get_model_name()
                assert "claude-sonnet-4-5-20250929" in client.get_model_name()

    def test_get_model_name_for_grok(self):
        """Test get_model_name returns correct name for Grok"""
        with patch.dict(os.environ, {'MODEL_MODE': 'grok', 'GROK_API_KEY': 'test_key',
                                     'GROK_MODEL': 'grok-4-fast-reasoning'}):
            with patch('src.grok_handler.GrokHandler'):
                client = UniversalModelClient(model_mode='grok')
                assert "Grok" in client.get_model_name()

    def test_get_model_name_for_local(self):
        """Test get_model_name returns correct name for Local LLM"""
        with patch.dict(os.environ, {'MODEL_MODE': 'local', 'LOCAL_MODEL_NAME': 'llama3.1:latest'}):
            with patch('src.local_llm_handler.LocalLLMHandler') as mock_local_class:
                mock_local = Mock()
                mock_local.model_name = "llama3.1:latest"
                mock_local_class.return_value = mock_local

                client = UniversalModelClient(model_mode='local')
                assert "Local LLM" in client.get_model_name()
                assert "llama3.1:latest" in client.get_model_name()

    def test_auto_detect_mode_from_env(self):
        """Test that model mode is auto-detected from environment"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                client = UniversalModelClient()  # No mode specified
                assert client.model_mode == 'api'

    def test_max_tokens_limits(self):
        """Test that max_tokens are properly limited for different models"""
        with patch.dict(os.environ, {'MODEL_MODE': 'grok', 'GROK_API_KEY': 'test_key',
                                     'GROK_MAX_TOKENS': '8192'}):
            with patch('src.grok_handler.GrokHandler') as mock_grok_class:
                mock_grok = Mock()
                mock_grok.generate_response.return_value = "Test response"
                mock_grok_class.return_value = mock_grok

                client = UniversalModelClient(model_mode='grok')
                client.generate("Test", max_tokens=10000)  # Request more than limit

                # Verify max_tokens was capped at 8192
                call_args = mock_grok.generate_response.call_args
                assert call_args[1]['max_tokens'] <= 8192


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
