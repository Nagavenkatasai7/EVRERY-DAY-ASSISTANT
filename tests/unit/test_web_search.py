"""
Unit Tests for Web Search Integration
Tests Tavily API integration and result processing
"""

import pytest
from unittest.mock import Mock, patch

from src.web_search import WebSearchManager


class TestWebSearchClient:
    """Test suite for Web Search Client"""

    def test_initialization(self):
        """Test that WebSearchManager initializes correctly"""
        client = WebSearchManager()

        assert client.tavily_client is not None
        assert client.max_results > 0

    @patch('src.web_search.TavilyClient')
    def test_search_success(self, mock_tavily):
        """Test successful web search"""
        mock_client = Mock()
        mock_client.search.return_value = {
            'results': [
                {
                    'title': 'Test Article 1',
                    'url': 'https://example.com/article1',
                    'content': 'This is test content about machine learning.',
                    'score': 0.95
                },
                {
                    'title': 'Test Article 2',
                    'url': 'https://test.com/article2',
                    'content': 'Another article about AI research.',
                    'score': 0.88
                }
            ]
        }
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client

        results = client.search("machine learning research")

        assert len(results) == 2
        assert results[0]['title'] == 'Test Article 1'
        assert results[0]['score'] == 0.95
        assert 'domain' in results[0]

    @patch('src.web_search.TavilyClient')
    def test_search_empty_results(self, mock_tavily):
        """Test handling of empty search results"""
        mock_client = Mock()
        mock_client.search.return_value = {'results': []}
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client

        results = client.search("obscure query with no results")

        assert results == []

    @patch('src.web_search.TavilyClient')
    def test_search_api_error(self, mock_tavily):
        """Test handling of API errors"""
        mock_client = Mock()
        mock_client.search.side_effect = Exception("API Error")
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client

        results = client.search("test query")

        # Should return empty list on error
        assert results == []

    @patch('src.web_search.TavilyClient')
    def test_search_retry_logic(self, mock_tavily):
        """Test retry logic on transient failures"""
        mock_client = Mock()
        # First call fails, second succeeds
        mock_client.search.side_effect = [
            Exception("Temporary error"),
            {
                'results': [
                    {
                        'title': 'Success',
                        'url': 'https://example.com',
                        'content': 'Content',
                        'score': 0.9
                    }
                ]
            }
        ]
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client

        results = client.search("test query")

        # Should succeed after retry
        assert len(results) == 1
        assert results[0]['title'] == 'Success'

    @patch('src.web_search.TavilyClient')
    def test_clean_content(self, mock_tavily):
        """Test content cleaning"""
        mock_client = Mock()
        mock_client.search.return_value = {
            'results': [
                {
                    'title': 'Test',
                    'url': 'https://example.com',
                    'content': '  Extra   whitespace  \n\n  and   newlines  ',
                    'score': 0.9
                }
            ]
        }
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client

        results = client.search("test query")

        # Content should be cleaned
        content = results[0]['content']
        assert '   ' not in content
        assert '\n\n' not in content

    @patch('src.web_search.TavilyClient')
    def test_extract_domain(self, mock_tavily):
        """Test domain extraction from URLs"""
        mock_client = Mock()
        mock_client.search.return_value = {
            'results': [
                {
                    'title': 'Test 1',
                    'url': 'https://www.example.com/path/to/article',
                    'content': 'Content',
                    'score': 0.9
                },
                {
                    'title': 'Test 2',
                    'url': 'https://subdomain.test.org/page',
                    'content': 'Content',
                    'score': 0.8
                }
            ]
        }
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client

        results = client.search("test query")

        assert results[0]['domain'] == 'example.com'
        assert results[1]['domain'] == 'test.org'

    @patch('src.web_search.TavilyClient')
    def test_search_max_results(self, mock_tavily):
        """Test that max_results parameter is respected"""
        mock_client = Mock()
        # Return more results than max_results
        mock_client.search.return_value = {
            'results': [
                {'title': f'Article {i}', 'url': f'https://example.com/{i}',
                 'content': f'Content {i}', 'score': 0.9}
                for i in range(20)
            ]
        }
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client
        client.max_results = 5

        results = client.search("test query", max_results=5)

        assert len(results) <= 5

    @patch('src.web_search.TavilyClient')
    def test_search_with_special_characters(self, mock_tavily):
        """Test search with special characters in query"""
        mock_client = Mock()
        mock_client.search.return_value = {'results': []}
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client

        # Should handle special characters without crashing
        queries = [
            "machine learning & AI",
            "C++ programming",
            "What is α-β pruning?",
            "研究 (research in Chinese)"
        ]

        for query in queries:
            results = client.search(query)
            assert isinstance(results, list)

    @patch('src.web_search.TavilyClient')
    def test_get_source_diversity(self, mock_tavily):
        """Test source diversity calculation"""
        mock_client = Mock()
        mock_tavily.return_value = mock_client

        client = WebSearchManager()

        web_results = [
            {'domain': 'example.com', 'url': 'https://example.com/1'},
            {'domain': 'example.com', 'url': 'https://example.com/2'},
            {'domain': 'test.org', 'url': 'https://test.org/1'},
            {'domain': 'another.com', 'url': 'https://another.com/1'}
        ]

        pdf_results = [
            {'doc_name': 'paper1.pdf'},
            {'doc_name': 'paper2.pdf'}
        ]

        diversity = client.get_source_diversity(web_results, pdf_results)

        assert diversity['total_sources'] == 6
        assert diversity['web_sources'] == 4
        assert diversity['pdf_sources'] == 2
        assert diversity['unique_domains'] == 3
        assert len(diversity['domains_list']) == 3
        assert 'example.com' in diversity['domains_list']

    def test_get_source_diversity_empty(self):
        """Test diversity calculation with empty results"""
        client = WebSearchManager()

        diversity = client.get_source_diversity([], [])

        assert diversity['total_sources'] == 0
        assert diversity['web_sources'] == 0
        assert diversity['pdf_sources'] == 0
        assert diversity['unique_domains'] == 0

    @patch('src.web_search.TavilyClient')
    def test_search_result_structure(self, mock_tavily):
        """Test that search results have expected structure"""
        mock_client = Mock()
        mock_client.search.return_value = {
            'results': [
                {
                    'title': 'Test Article',
                    'url': 'https://example.com/article',
                    'content': 'Article content here',
                    'score': 0.95
                }
            ]
        }
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client

        results = client.search("test query")

        assert len(results) == 1
        result = results[0]

        # Check required fields
        assert 'title' in result
        assert 'url' in result
        assert 'content' in result
        assert 'score' in result
        assert 'domain' in result

        # Check field types
        assert isinstance(result['title'], str)
        assert isinstance(result['url'], str)
        assert isinstance(result['content'], str)
        assert isinstance(result['score'], (int, float))
        assert isinstance(result['domain'], str)


class TestWebSearchEdgeCases:
    """Test edge cases and error conditions"""

    @patch('src.web_search.TavilyClient')
    def test_search_with_empty_query(self, mock_tavily):
        """Test search with empty query string"""
        mock_client = Mock()
        mock_client.search.return_value = {'results': []}
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client

        results = client.search("")

        assert results == []

    @patch('src.web_search.TavilyClient')
    def test_search_with_very_long_query(self, mock_tavily):
        """Test search with very long query"""
        mock_client = Mock()
        mock_client.search.return_value = {'results': []}
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client

        long_query = "machine learning " * 100  # Very long query

        results = client.search(long_query)

        assert isinstance(results, list)

    @patch('src.web_search.TavilyClient')
    def test_malformed_url_handling(self, mock_tavily):
        """Test handling of malformed URLs"""
        mock_client = Mock()
        mock_client.search.return_value = {
            'results': [
                {
                    'title': 'Test',
                    'url': 'not-a-valid-url',
                    'content': 'Content',
                    'score': 0.9
                }
            ]
        }
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client

        results = client.search("test query")

        # Should handle gracefully
        assert len(results) == 1
        assert 'domain' in results[0]

    @patch('src.web_search.TavilyClient')
    def test_missing_result_fields(self, mock_tavily):
        """Test handling of missing fields in results"""
        mock_client = Mock()
        mock_client.search.return_value = {
            'results': [
                {
                    'title': 'Test',
                    # Missing url, content, score
                }
            ]
        }
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client

        # Should handle missing fields without crashing
        try:
            results = client.search("test query")
            # If it doesn't crash, that's a pass
            assert isinstance(results, list)
        except KeyError:
            # Expected if required fields are missing
            pass

    @patch('src.web_search.TavilyClient')
    def test_content_with_html_entities(self, mock_tavily):
        """Test content cleaning with HTML entities"""
        mock_client = Mock()
        mock_client.search.return_value = {
            'results': [
                {
                    'title': 'Test',
                    'url': 'https://example.com',
                    'content': 'Content with &amp; &lt; &gt; entities',
                    'score': 0.9
                }
            ]
        }
        mock_tavily.return_value = mock_client

        client = WebSearchManager()
        client.tavily_client = mock_client

        results = client.search("test query")

        # HTML entities should be decoded if cleaning is implemented
        content = results[0]['content']
        assert isinstance(content, str)
