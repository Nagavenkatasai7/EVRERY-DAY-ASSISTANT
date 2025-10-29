"""
Comprehensive Trend Discovery Tests
Tests Tavily API integration, caching, and relevance scoring

Coverage targets:
- Tavily API integration
- Trend caching and retrieval
- Relevance scoring algorithms
- Deduplication logic
- Connection to user projects
- Category-based discovery
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from src.social_media.trend_discovery import TrendDiscovery
from src.social_media.models import TrendingTopic, DatabaseManager


# ==================== Initialization Tests ====================

@pytest.mark.unit
class TestTrendDiscoveryInit:
    """Test TrendDiscovery initialization"""

    def test_init_with_api_key(self, mock_tavily, sm_db_manager):
        """Test initialization with API key"""
        discovery = TrendDiscovery(
            api_key="test_tavily_key",
            db_manager=sm_db_manager
        )

        assert discovery.api_key == "test_tavily_key"
        assert discovery.client is not None
        assert discovery.db_manager is sm_db_manager

    def test_init_without_api_key(self, mock_tavily):
        """Test initialization fails without API key"""
        with patch('src.social_media.trend_discovery.TAVILY_API_KEY', None):
            with pytest.raises(ValueError):
                TrendDiscovery(api_key=None)

    def test_init_with_default_db(self, mock_tavily):
        """Test initialization with default database manager"""
        with patch('src.social_media.trend_discovery.TAVILY_API_KEY', 'test_key'):
            discovery = TrendDiscovery()

            assert discovery.db_manager is not None

    def test_trend_categories_defined(self, mock_tavily, sm_db_manager):
        """Test trend categories are properly defined"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        assert 'ai_research' in discovery.TREND_CATEGORIES
        assert 'job_market' in discovery.TREND_CATEGORIES
        assert 'tech_news' in discovery.TREND_CATEGORIES
        assert 'tools_frameworks' in discovery.TREND_CATEGORIES


# ==================== Weekly Trends Discovery Tests ====================

@pytest.mark.unit
class TestDiscoverWeeklyTrends:
    """Test weekly trends discovery"""

    def test_discover_all_categories(self, mock_tavily, sm_db_manager):
        """Test discovering trends across all categories"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = discovery.discover_weekly_trends()

        assert isinstance(trends, dict)
        assert len(trends) > 0
        assert 'ai_research' in trends or 'job_market' in trends

    def test_discover_specific_categories(self, mock_tavily, sm_db_manager):
        """Test discovering trends for specific categories"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = discovery.discover_weekly_trends(
            categories=['ai_research', 'tech_news']
        )

        assert 'ai_research' in trends or 'tech_news' in trends

    def test_discover_with_max_results(self, mock_tavily, sm_db_manager):
        """Test max_results parameter limits trends per category"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = discovery.discover_weekly_trends(
            categories=['ai_research'],
            max_results_per_category=3
        )

        # Each category should have at most 3 trends
        for category_trends in trends.values():
            assert len(category_trends) <= 3

    def test_trends_sorted_by_relevance(self, mock_tavily, sm_db_manager):
        """Test trends are sorted by relevance score"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = discovery.discover_weekly_trends(
            categories=['ai_research'],
            max_results_per_category=5
        )

        for category_trends in trends.values():
            if len(category_trends) > 1:
                # Check descending order
                scores = [t['relevance_score'] for t in category_trends]
                assert scores == sorted(scores, reverse=True)


# ==================== Search Trends Tests ====================

@pytest.mark.unit
class TestSearchTrends:
    """Test _search_trends method"""

    def test_search_trends_success(self, mock_tavily, sm_db_manager):
        """Test successful trend search"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = discovery._search_trends(
            query="RAG systems 2025",
            category="ai_research",
            max_results=5
        )

        assert isinstance(trends, list)
        assert len(trends) > 0
        assert all('topic' in t for t in trends)
        assert all('relevance_score' in t for t in trends)

    def test_search_trends_with_caching(self, mock_tavily, sm_db_manager):
        """Test trend search uses cache"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        # First search - should hit API
        trends1 = discovery._search_trends(
            query="test query",
            category="ai_research",
            max_results=5
        )

        # Cache the first result
        if trends1:
            discovery._cache_trend(trends1[0], expire_days=7)

        # Second search - should use cache
        trends2 = discovery._search_trends(
            query="test query",
            category="ai_research",
            max_results=5
        )

        assert len(trends2) > 0

    def test_search_trends_api_error(self, mock_tavily, sm_db_manager):
        """Test handling API errors"""
        mock_tavily.return_value.search.side_effect = Exception("API Error")

        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = discovery._search_trends(
            query="test query",
            category="ai_research"
        )

        # Should return empty list on error
        assert trends == []

    def test_search_trends_empty_response(self, mock_tavily, sm_db_manager):
        """Test handling empty API response"""
        mock_tavily.return_value.search.return_value = {'results': []}

        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = discovery._search_trends(
            query="obscure query",
            category="ai_research"
        )

        assert trends == []


# ==================== Relevance Calculation Tests ====================

@pytest.mark.unit
class TestCalculateRelevance:
    """Test relevance scoring algorithm"""

    def test_calculate_relevance_research_keywords(self, mock_tavily, sm_db_manager):
        """Test relevance boost for research keywords"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trend = {
            'topic': 'New research paper on AI architectures',
            'summary': 'Study shows improved model performance and training efficiency',
            'relevance_score': 0.5
        }

        score = discovery._calculate_relevance(trend)

        # Should be boosted due to research keywords
        assert score > 0.5

    def test_calculate_relevance_job_keywords(self, mock_tavily, sm_db_manager):
        """Test relevance boost for job-seeking keywords"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trend = {
            'topic': 'AI companies hiring engineers',
            'summary': 'Multiple opportunities for ML career positions with competitive salary',
            'relevance_score': 0.5
        }

        score = discovery._calculate_relevance(trend)

        assert score > 0.5

    def test_calculate_relevance_tool_keywords(self, mock_tavily, sm_db_manager):
        """Test relevance boost for tool/framework keywords"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trend = {
            'topic': 'New LangChain framework features',
            'summary': 'Tutorial shows implementation with code examples on GitHub',
            'relevance_score': 0.5
        }

        score = discovery._calculate_relevance(trend)

        assert score > 0.5

    def test_calculate_relevance_multiple_boosts(self, mock_tavily, sm_db_manager):
        """Test relevance with multiple keyword categories"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trend = {
            'topic': 'Research on new ML framework for hiring',
            'summary': 'Paper presents implementation guide with code and benchmarks',
            'relevance_score': 0.3
        }

        score = discovery._calculate_relevance(trend)

        # Should get multiple boosts
        assert score > 0.5

    def test_calculate_relevance_capped_at_one(self, mock_tavily, sm_db_manager):
        """Test relevance score capped at 1.0"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trend = {
            'topic': 'Revolutionary research paper on innovative ML model',
            'summary': 'Study shows benchmark performance with implementation tutorial',
            'relevance_score': 0.9
        }

        score = discovery._calculate_relevance(trend)

        assert score <= 1.0


# ==================== Deduplication Tests ====================

@pytest.mark.unit
class TestDeduplicateTrends:
    """Test trend deduplication logic"""

    def test_deduplicate_identical_trends(self, mock_tavily, sm_db_manager):
        """Test deduplication removes identical trends"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = [
            {'topic': 'GPT-5 announcement from OpenAI', 'relevance_score': 0.9},
            {'topic': 'OpenAI announces GPT-5 release', 'relevance_score': 0.85},
        ]

        unique = discovery._deduplicate_trends(trends)

        # Should remove one duplicate
        assert len(unique) == 1

    def test_deduplicate_similar_topics(self, mock_tavily, sm_db_manager):
        """Test deduplication removes similar topics"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = [
            {'topic': 'Machine learning model optimization techniques', 'relevance_score': 0.9},
            {'topic': 'Optimization techniques for machine learning models', 'relevance_score': 0.8},
            {'topic': 'Quantum computing breakthrough', 'relevance_score': 0.7}
        ]

        unique = discovery._deduplicate_trends(trends)

        # Should keep first ML trend and quantum trend
        assert len(unique) == 2

    def test_deduplicate_diverse_topics(self, mock_tavily, sm_db_manager):
        """Test deduplication keeps diverse topics"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = [
            {'topic': 'RAG systems improvements', 'relevance_score': 0.9},
            {'topic': 'New AI hiring trends', 'relevance_score': 0.8},
            {'topic': 'Quantum computing progress', 'relevance_score': 0.7}
        ]

        unique = discovery._deduplicate_trends(trends)

        # All should be kept (diverse)
        assert len(unique) == 3

    def test_deduplicate_empty_list(self, mock_tavily, sm_db_manager):
        """Test deduplication with empty list"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        unique = discovery._deduplicate_trends([])

        assert unique == []


# ==================== Caching Tests ====================

@pytest.mark.unit
class TestTrendCaching:
    """Test trend caching functionality"""

    def test_cache_trend(self, mock_tavily, sm_db_manager, sm_session):
        """Test caching a trend"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trend = {
            'topic': 'Test Trend',
            'category': 'ai_research',
            'search_query': 'test query',
            'url': 'https://example.com',
            'summary': 'Test summary',
            'relevance_score': 0.9
        }

        discovery._cache_trend(trend, expire_days=7)

        # Verify cached in database
        cached = sm_session.query(TrendingTopic).filter(
            TrendingTopic.topic == 'Test Trend'
        ).first()

        assert cached is not None
        assert cached.relevance_score == 0.9
        assert cached.category == 'ai_research'

    def test_get_cached_trends(self, mock_tavily, sm_db_manager, sm_session):
        """Test retrieving cached trends"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        # Cache a trend
        cached_trend = TrendingTopic(
            topic="Cached Trend",
            category="ai_research",
            search_query="test query",
            source_urls=["https://example.com"],
            summary="Cached summary",
            relevance_score=0.85,
            discovered_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        sm_session.add(cached_trend)
        sm_session.commit()

        # Retrieve cached trends
        trends = discovery._get_cached_trends("test query", max_age_days=7)

        assert len(trends) > 0
        assert trends[0]['topic'] == "Cached Trend"
        assert trends[0]['cached'] is True

    def test_get_cached_trends_expired(self, mock_tavily, sm_db_manager, sm_session):
        """Test expired trends are not retrieved"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        # Cache an expired trend
        expired_trend = TrendingTopic(
            topic="Expired Trend",
            category="ai_research",
            search_query="expired query",
            relevance_score=0.8,
            discovered_at=datetime.utcnow() - timedelta(days=10),
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        sm_session.add(expired_trend)
        sm_session.commit()

        # Try to retrieve
        trends = discovery._get_cached_trends("expired query", max_age_days=7)

        # Should not return expired trend
        assert len(trends) == 0

    def test_cache_trend_error_handling(self, mock_tavily, sm_db_manager):
        """Test cache error handling"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        # Try to cache invalid trend
        invalid_trend = {'invalid': 'data'}

        # Should not raise exception
        discovery._cache_trend(invalid_trend, expire_days=7)


# ==================== Connection to Projects Tests ====================

@pytest.mark.unit
class TestConnectTrendToProjects:
    """Test connecting trends to user projects"""

    def test_connect_high_relevance(self, mock_tavily, sm_db_manager):
        """Test connecting highly relevant trend"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trend = {
            'topic': 'RAG system optimization techniques',
            'summary': 'New research on retrieval augmented generation systems'
        }

        connection = discovery.connect_trend_to_projects(
            trend=trend,
            user_projects=['RAG Chatbot', 'Research Assistant with RAG'],
            research_area='Retrieval Augmented Generation systems'
        )

        assert connection['connection_angle'] == 'high_relevance'
        assert connection['connection_strength'] > 0.2

    def test_connect_moderate_relevance(self, mock_tavily, sm_db_manager):
        """Test connecting moderately relevant trend"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trend = {
            'topic': 'Multi-agent AI systems',
            'summary': 'Research on agent coordination patterns'
        }

        connection = discovery.connect_trend_to_projects(
            trend=trend,
            user_projects=['RAG Chatbot', 'AI Research Assistant'],
            research_area='Machine Learning applications'
        )

        assert connection['connection_angle'] in ['moderate_relevance', 'industry_awareness']

    def test_connect_low_relevance(self, mock_tavily, sm_db_manager):
        """Test connecting low relevance trend"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trend = {
            'topic': 'Quantum computing breakthrough',
            'summary': 'New quantum processor design'
        }

        connection = discovery.connect_trend_to_projects(
            trend=trend,
            user_projects=['Web Development', 'Mobile Apps'],
            research_area='Software Engineering'
        )

        assert connection['connection_angle'] == 'industry_awareness'
        assert connection['connection_strength'] < 0.3

    def test_connect_includes_overlapping_concepts(self, mock_tavily, sm_db_manager):
        """Test connection identifies overlapping concepts"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trend = {
            'topic': 'Machine learning optimization techniques',
            'summary': 'Advanced training methods for neural networks'
        }

        connection = discovery.connect_trend_to_projects(
            trend=trend,
            user_projects=['Neural Network Training', 'ML Optimization'],
            research_area='Machine Learning Systems'
        )

        assert 'overlapping_concepts' in connection
        assert len(connection['overlapping_concepts']) > 0

    def test_connect_provides_suggestions(self, mock_tavily, sm_db_manager):
        """Test connection provides content approach suggestions"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trend = {
            'topic': 'Test trend',
            'summary': 'Test summary'
        }

        connection = discovery.connect_trend_to_projects(
            trend=trend,
            user_projects=['Test Project'],
            research_area='Test Research'
        )

        assert 'suggested_approach' in connection
        assert isinstance(connection['suggested_approach'], str)


# ==================== Best Trends for User Tests ====================

@pytest.mark.unit
class TestGetBestTrendsForUser:
    """Test getting best trends for specific user"""

    def test_get_best_trends_success(self, mock_tavily, sm_db_manager):
        """Test getting best trends for user"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = discovery.get_best_trends_for_user(
            user_research_area="RAG systems and multi-agent AI",
            user_projects=["Research Assistant", "Multi-agent System"],
            num_trends=3
        )

        assert isinstance(trends, list)
        assert len(trends) <= 3
        assert all('trend' in t for t in trends)
        assert all('connection_strength' in t for t in trends)

    def test_trends_sorted_by_connection(self, mock_tavily, sm_db_manager):
        """Test trends sorted by connection strength"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = discovery.get_best_trends_for_user(
            user_research_area="AI systems",
            user_projects=["AI Project"],
            num_trends=5
        )

        if len(trends) > 1:
            # Check descending order by connection strength
            strengths = [t['connection_strength'] for t in trends]
            assert strengths == sorted(strengths, reverse=True)

    def test_respects_num_trends_limit(self, mock_tavily, sm_db_manager):
        """Test num_trends parameter limits results"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = discovery.get_best_trends_for_user(
            user_research_area="AI",
            user_projects=["Project"],
            num_trends=2
        )

        assert len(trends) <= 2


# ==================== Integration Tests ====================

@pytest.mark.integration
class TestTrendDiscoveryIntegration:
    """Integration tests for TrendDiscovery"""

    def test_full_discovery_workflow(self, mock_tavily, sm_db_manager):
        """Test complete trend discovery workflow"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        # Discover trends
        all_trends = discovery.discover_weekly_trends(
            categories=['ai_research'],
            max_results_per_category=5
        )

        assert len(all_trends) > 0

        # Get best trends for user
        if all_trends:
            best_trends = discovery.get_best_trends_for_user(
                user_research_area="AI Research",
                user_projects=["Research Assistant"],
                num_trends=3
            )

            assert len(best_trends) > 0

    def test_caching_workflow(self, mock_tavily, sm_db_manager, sm_session):
        """Test caching and retrieval workflow"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        # First search - cache results
        trends1 = discovery._search_trends(
            query="AI research",
            category="ai_research",
            max_results=5
        )

        if trends1:
            discovery._cache_trend(trends1[0], expire_days=7)

        # Verify cached
        cached = sm_session.query(TrendingTopic).filter(
            TrendingTopic.search_query == "AI research"
        ).all()

        assert len(cached) > 0

        # Second search - should use cache
        trends2 = discovery._get_cached_trends("AI research", max_age_days=7)

        assert len(trends2) > 0


# ==================== API Tests (marked for manual run) ====================

@pytest.mark.api
class TestTrendDiscoveryAPIIntegration:
    """Tests that hit real Tavily API (require valid credentials)"""

    @pytest.mark.skip(reason="Requires valid Tavily API key")
    def test_real_trend_search(self):
        """Test real Tavily API search"""
        import os

        discovery = TrendDiscovery(api_key=os.getenv('TAVILY_API_KEY'))

        trends = discovery._search_trends(
            query="AI research 2025",
            category="ai_research",
            max_results=3
        )

        assert len(trends) > 0
        print(f"Found {len(trends)} trends")
        for trend in trends:
            print(f"- {trend['topic']}: {trend['relevance_score']}")

    @pytest.mark.skip(reason="Requires valid Tavily API key")
    def test_real_weekly_discovery(self):
        """Test real weekly trends discovery"""
        import os

        discovery = TrendDiscovery(api_key=os.getenv('TAVILY_API_KEY'))

        all_trends = discovery.discover_weekly_trends(
            categories=['ai_research', 'tech_news'],
            max_results_per_category=3
        )

        assert len(all_trends) > 0
        print(f"Discovered trends in {len(all_trends)} categories")
