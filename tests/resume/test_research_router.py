"""
Unit tests for ResearchRouter
Tests routing between Perplexity and Tavily APIs
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.resume_utils.research_router import ResearchRouter


class TestResearchRouter:
    """Test suite for ResearchRouter"""

    def test_init_with_tavily(self):
        """Test initialization with Tavily API"""
        with patch.dict(os.environ, {'RESUME_RESEARCH_API': 'tavily', 'TAVILY_API_KEY': 'test_key'}):
            with patch('src.resume_utils.research_router.WebSearchClient', create=True) as mock_tavily:
                router = ResearchRouter(research_api='tavily')

                assert router.research_api == 'tavily'
                assert router.tavily_client is not None
                assert router.perplexity_client is None
                mock_tavily.assert_called_once()

    def test_init_with_perplexity(self):
        """Test initialization with Perplexity API"""
        with patch.dict(os.environ, {'RESUME_RESEARCH_API': 'perplexity', 'PERPLEXITY_API_KEY': 'test_key'}):
            with patch('src.resume_utils.research_router.PerplexityClient') as mock_perplexity:
                router = ResearchRouter(research_api='perplexity')

                assert router.research_api == 'perplexity'
                assert router.perplexity_client is not None
                assert router.tavily_client is None
                mock_perplexity.assert_called_once()

    def test_auto_detect_from_env(self):
        """Test that research API is auto-detected from environment"""
        with patch.dict(os.environ, {'RESUME_RESEARCH_API': 'tavily', 'TAVILY_API_KEY': 'test_key'}):
            with patch('src.resume_utils.research_router.WebSearchClient', create=True):
                router = ResearchRouter()  # No API specified
                assert router.research_api == 'tavily'

    def test_fallback_to_tavily_if_perplexity_key_missing(self):
        """Test fallback from Perplexity to Tavily if key is missing"""
        with patch.dict(os.environ, {'TAVILY_API_KEY': 'test_key'}, clear=True):
            with patch('src.resume_utils.research_router.WebSearchClient', create=True):
                router = ResearchRouter(research_api='perplexity')

                # Should fall back to tavily
                assert router.research_api == 'tavily'

    def test_disabled_if_no_api_keys(self):
        """Test that research is disabled if no API keys available"""
        with patch.dict(os.environ, {}, clear=True):
            router = ResearchRouter(research_api='tavily')

            assert router.research_api is None

    def test_research_company_with_perplexity(self):
        """Test company research with Perplexity"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            with patch('src.resume_utils.research_router.PerplexityClient') as mock_perplexity_class:
                mock_perplexity = Mock()
                mock_perplexity.research_company.return_value = {
                    'research': 'Test company research from Perplexity'
                }
                mock_perplexity_class.return_value = mock_perplexity

                router = ResearchRouter(research_api='perplexity')
                result = router.research_company("Google", "Software Engineer")

                assert result is not None
                assert result['company_name'] == 'Google'
                assert result['source'] == 'Perplexity AI'
                assert 'research' in result
                mock_perplexity.research_company.assert_called_once_with("Google", "Software Engineer")

    def test_research_company_with_tavily(self):
        """Test company research with Tavily"""
        with patch.dict(os.environ, {'TAVILY_API_KEY': 'test_key'}):
            with patch('src.resume_utils.research_router.WebSearchClient', create=True) as mock_tavily_class:
                mock_tavily = Mock()
                mock_tavily.search.return_value = [
                    {
                        'title': 'About Google',
                        'content': 'Google is a tech company...',
                        'url': 'https://google.com/about'
                    },
                    {
                        'title': 'Google Careers',
                        'content': 'Join Google...',
                        'url': 'https://careers.google.com'
                    }
                ]
                mock_tavily_class.return_value = mock_tavily

                router = ResearchRouter(research_api='tavily')
                result = router.research_company("Google", "Software Engineer")

                assert result is not None
                assert result['company_name'] == 'Google'
                assert result['source'] == 'Tavily Search'
                assert 'research' in result
                assert 'About Google' in result['research']
                mock_tavily.search.assert_called_once()

    def test_research_company_query_building(self):
        """Test that search queries are properly constructed"""
        with patch.dict(os.environ, {'TAVILY_API_KEY': 'test_key'}):
            with patch('src.resume_utils.research_router.WebSearchClient', create=True) as mock_tavily_class:
                mock_tavily = Mock()
                mock_tavily.search.return_value = []
                mock_tavily_class.return_value = mock_tavily

                router = ResearchRouter(research_api='tavily')

                # Test with job title
                router.research_company("Google", "Software Engineer")
                query_with_title = mock_tavily.search.call_args[0][0]
                assert 'Google' in query_with_title
                assert 'Software Engineer' in query_with_title
                assert 'technologies' in query_with_title

                # Test without job title
                router.research_company("Microsoft")
                query_without_title = mock_tavily.search.call_args[0][0]
                assert 'Microsoft' in query_without_title
                assert 'recent news' in query_without_title

    def test_research_returns_none_if_disabled(self):
        """Test that research returns None if research API is disabled"""
        with patch.dict(os.environ, {}, clear=True):
            router = ResearchRouter()
            result = router.research_company("Google")

            assert result is None

    def test_research_handles_perplexity_error(self):
        """Test that Perplexity API errors are handled gracefully"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            with patch('src.resume_utils.research_router.PerplexityClient') as mock_perplexity_class:
                mock_perplexity = Mock()
                mock_perplexity.research_company.side_effect = Exception("API Error")
                mock_perplexity_class.return_value = mock_perplexity

                router = ResearchRouter(research_api='perplexity')
                result = router.research_company("Google")

                # Should return None on error
                assert result is None

    def test_research_handles_tavily_error(self):
        """Test that Tavily API errors are handled gracefully"""
        with patch.dict(os.environ, {'TAVILY_API_KEY': 'test_key'}):
            with patch('src.resume_utils.research_router.WebSearchClient', create=True) as mock_tavily_class:
                mock_tavily = Mock()
                mock_tavily.search.side_effect = Exception("API Error")
                mock_tavily_class.return_value = mock_tavily

                router = ResearchRouter(research_api='tavily')
                result = router.research_company("Google")

                # Should return None on error
                assert result is None

    def test_get_api_name_for_perplexity(self):
        """Test get_api_name returns correct name for Perplexity"""
        with patch.dict(os.environ, {'PERPLEXITY_API_KEY': 'test_key'}):
            with patch('src.resume_utils.research_router.PerplexityClient'):
                router = ResearchRouter(research_api='perplexity')
                assert router.get_api_name() == 'Perplexity AI'

    def test_get_api_name_for_tavily(self):
        """Test get_api_name returns correct name for Tavily"""
        with patch.dict(os.environ, {'TAVILY_API_KEY': 'test_key'}):
            with patch('src.resume_utils.research_router.WebSearchClient', create=True):
                router = ResearchRouter(research_api='tavily')
                assert router.get_api_name() == 'Tavily Search'

    def test_get_api_name_when_disabled(self):
        """Test get_api_name returns disabled message when no API configured"""
        with patch.dict(os.environ, {}, clear=True):
            router = ResearchRouter()
            assert router.get_api_name() == 'None (Disabled)'

    def test_tavily_result_formatting(self):
        """Test that Tavily results are properly formatted"""
        with patch.dict(os.environ, {'TAVILY_API_KEY': 'test_key'}):
            with patch('src.resume_utils.research_router.WebSearchClient', create=True) as mock_tavily_class:
                mock_tavily = Mock()
                mock_tavily.search.return_value = [
                    {'title': 'Result 1', 'content': 'Content 1', 'url': 'http://example.com/1'},
                    {'title': 'Result 2', 'content': 'Content 2', 'url': 'http://example.com/2'},
                    {'title': 'Result 3', 'content': 'Content 3', 'url': 'http://example.com/3'},
                ]
                mock_tavily_class.return_value = mock_tavily

                router = ResearchRouter(research_api='tavily')
                result = router.research_company("TestCorp")

                # Check formatting
                research_text = result['research']
                assert 'Company Research for TestCorp' in research_text
                assert '1. Result 1' in research_text
                assert 'Content 1' in research_text
                assert 'Source: http://example.com/1' in research_text

    def test_max_results_limit_for_tavily(self):
        """Test that Tavily search limits results to 3"""
        with patch.dict(os.environ, {'TAVILY_API_KEY': 'test_key'}):
            with patch('src.resume_utils.research_router.WebSearchClient', create=True) as mock_tavily_class:
                mock_tavily = Mock()
                mock_tavily.search.return_value = []
                mock_tavily_class.return_value = mock_tavily

                router = ResearchRouter(research_api='tavily')
                router.research_company("TestCorp")

                # Verify max_results=3 was passed
                call_args = mock_tavily.search.call_args
                assert call_args[1]['max_results'] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
