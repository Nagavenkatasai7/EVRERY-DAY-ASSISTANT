"""
Comprehensive tests for PerplexityClient
Tests API integration and error handling
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
import requests

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.resume_utils.perplexity_client import PerplexityClient


class TestPerplexityClient:
    """Test suite for PerplexityClient"""

    def test_init_with_api_key(self):
        """Test initialization with API key"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            client = PerplexityClient()
            assert client.api_key == 'test_key'
            assert client.base_url == 'https://api.perplexity.ai'

    def test_init_without_api_key(self):
        """Test initialization without API key"""
        with patch.dict(os.environ, {}, clear=True):
            client = PerplexityClient()
            assert client.api_key is None

    def test_research_company_without_api_key(self):
        """Test research_company returns None when API key is missing"""
        with patch.dict(os.environ, {}, clear=True):
            client = PerplexityClient()
            result = client.research_company("Google")
            assert result is None

    def test_research_company_success(self):
        """Test successful company research"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            client = PerplexityClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'choices': [{
                    'message': {
                        'content': 'Google is a technology company known for search, AI, and cloud services.'
                    }
                }]
            }

            with patch('requests.post', return_value=mock_response) as mock_post:
                result = client.research_company("Google")

                assert result is not None
                assert result['company_name'] == 'Google'
                assert 'Google is a technology company' in result['research']
                assert 'query' in result

                # Verify API was called correctly
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert 'api.perplexity.ai' in call_args[0][0]

    def test_research_company_with_job_title(self):
        """Test company research with job title"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            client = PerplexityClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'choices': [{
                    'message': {
                        'content': 'Software Engineers at Google work with Python, C++, and Go.'
                    }
                }]
            }

            with patch('requests.post', return_value=mock_response) as mock_post:
                result = client.research_company("Google", "Software Engineer")

                assert result is not None
                assert result['company_name'] == 'Google'
                assert 'Software Engineer' in result['query']

                # Check that query includes job title
                call_args = mock_post.call_args
                payload = call_args[1]['json']
                user_message = payload['messages'][1]['content']
                assert 'Software Engineer' in user_message
                assert 'Google' in user_message

    def test_research_company_without_job_title(self):
        """Test company research without job title"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            client = PerplexityClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'choices': [{
                    'message': {
                        'content': 'Microsoft is a leading technology company.'
                    }
                }]
            }

            with patch('requests.post', return_value=mock_response) as mock_post:
                result = client.research_company("Microsoft", job_title=None)

                assert result is not None
                assert result['company_name'] == 'Microsoft'

                # Check that query doesn't include job title keywords
                call_args = mock_post.call_args
                payload = call_args[1]['json']
                user_message = payload['messages'][1]['content']
                assert 'Microsoft' in user_message
                # Should use general query format
                assert 'technologies' in user_message or 'values' in user_message

    def test_research_company_api_error(self):
        """Test research_company handles API errors"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            client = PerplexityClient()

            mock_response = Mock()
            mock_response.status_code = 401  # Unauthorized
            mock_response.json.return_value = {'error': 'Invalid API key'}

            with patch('requests.post', return_value=mock_response):
                result = client.research_company("Google")
                assert result is None

    def test_research_company_network_error(self):
        """Test research_company handles network errors"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            client = PerplexityClient()

            with patch('requests.post', side_effect=requests.exceptions.RequestException("Network error")):
                result = client.research_company("Google")
                assert result is None

    def test_research_company_timeout(self):
        """Test research_company handles timeout"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            client = PerplexityClient()

            with patch('requests.post', side_effect=requests.exceptions.Timeout("Request timeout")):
                result = client.research_company("Amazon")
                assert result is None

    def test_research_company_api_headers(self):
        """Test that correct headers are sent to Perplexity API"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_api_key_123'}):
            client = PerplexityClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'Test content'}}]
            }

            with patch('requests.post', return_value=mock_response) as mock_post:
                client.research_company("TestCorp")

                # Verify headers
                call_args = mock_post.call_args
                headers = call_args[1]['headers']
                assert headers['Authorization'] == 'Bearer test_api_key_123'
                assert headers['Content-Type'] == 'application/json'

    def test_research_company_api_payload(self):
        """Test that correct payload is sent to Perplexity API"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            client = PerplexityClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'Test'}}]
            }

            with patch('requests.post', return_value=mock_response) as mock_post:
                client.research_company("StartupCo", "DevOps Engineer")

                # Verify payload structure
                call_args = mock_post.call_args
                payload = call_args[1]['json']

                assert payload['model'] == 'llama-3.1-sonar-small-128k-online'
                assert payload['max_tokens'] == 1000
                assert payload['temperature'] == 0.2
                assert len(payload['messages']) == 2
                assert payload['messages'][0]['role'] == 'system'
                assert payload['messages'][1]['role'] == 'user'

    def test_research_company_timeout_value(self):
        """Test that request has correct timeout"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            client = PerplexityClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'Test'}}]
            }

            with patch('requests.post', return_value=mock_response) as mock_post:
                client.research_company("TestCorp")

                # Verify timeout is set
                call_args = mock_post.call_args
                assert call_args[1]['timeout'] == 30

    def test_research_job_url(self):
        """Test research_job_url returns None (not implemented)"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            client = PerplexityClient()
            result = client.research_job_url("https://example.com/job/123")
            assert result is None

    def test_research_company_with_empty_response(self):
        """Test research_company with empty API response"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            client = PerplexityClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'choices': []}

            with patch('requests.post', return_value=mock_response):
                # Should raise an exception when accessing choices[0]
                result = client.research_company("Google")
                assert result is None

    def test_research_company_with_malformed_response(self):
        """Test research_company with malformed API response"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            client = PerplexityClient()

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'unexpected': 'structure'}

            with patch('requests.post', return_value=mock_response):
                result = client.research_company("Google")
                assert result is None

    def test_research_company_non_200_status(self):
        """Test research_company with non-200 status codes"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            client = PerplexityClient()

            # Test various error status codes
            error_codes = [400, 403, 404, 429, 500, 503]

            for status_code in error_codes:
                mock_response = Mock()
                mock_response.status_code = status_code

                with patch('requests.post', return_value=mock_response):
                    result = client.research_company("Google")
                    assert result is None, f"Should return None for status code {status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
