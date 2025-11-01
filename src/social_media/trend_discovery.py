"""
Trending Topics Discovery using Tavily API
Identifies relevant AI/ML trends for content generation
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from tavily import TavilyClient

from config.settings import TAVILY_API_KEY
from utils.logger import get_logger
from .models import TrendingTopic, DatabaseManager

logger = get_logger(__name__)


class TrendDiscovery:
    """
    Discovers trending AI/ML topics for social media content

    Features:
    - Uses Tavily API for real-time web search
    - Caches results to avoid redundant API calls
    - Scores relevance for CS/AI PhD students
    - Connects trends to user's research area
    """

    # Trending topic categories
    TREND_CATEGORIES = {
        'ai_research': [
            "latest AI research papers 2025",
            "RAG systems developments",
            "multi-agent AI architectures",
            "LLM reasoning capabilities",
            "AI safety and alignment 2025"
        ],
        'job_market': [
            "AI engineer jobs 2025",
            "AI/ML job market trends",
            "tech hiring AI specialists",
            "CS PhD career opportunities",
            "AI startup hiring"
        ],
        'tech_news': [
            "OpenAI latest updates",
            "Anthropic Claude developments",
            "Google AI announcements",
            "xAI Grok updates",
            "AI model releases 2025"
        ],
        'tools_frameworks': [
            "LangChain updates",
            "vector database comparisons",
            "AI agent frameworks",
            "prompt engineering tools",
            "RAG optimization techniques"
        ]
    }

    def __init__(self, api_key: str = None, db_manager: DatabaseManager = None):
        """Initialize trend discovery

        Args:
            api_key: Tavily API key (defaults to settings)
            db_manager: Database manager for caching
        """
        self.api_key = api_key or TAVILY_API_KEY
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY not set")

        self.client = TavilyClient(api_key=self.api_key)
        self.db_manager = db_manager or DatabaseManager()

        logger.info("Trend discovery initialized with Tavily API")

    def discover_weekly_trends(
        self,
        categories: List[str] = None,
        max_results_per_category: int = 5,
        force_refresh: bool = False
    ) -> Dict[str, List[Dict]]:
        """Discover trends across multiple categories

        Args:
            categories: List of category names (default: all)
            max_results_per_category: Max trends per category
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dict mapping category to list of trend dictionaries
        """
        if categories is None:
            categories = list(self.TREND_CATEGORIES.keys())

        all_trends = {}

        for category in categories:
            logger.info(f"Discovering trends in category: {category}")

            queries = self.TREND_CATEGORIES.get(category, [])
            category_trends = []

            for query in queries[:2]:  # Limit queries to avoid rate limits
                trends = self._search_trends(
                    query=query,
                    category=category,
                    max_results=max_results_per_category,
                    max_age_days=7,
                    force_refresh=force_refresh
                )
                category_trends.extend(trends)

            # Sort by relevance score
            category_trends.sort(key=lambda x: x['relevance_score'], reverse=True)

            # Deduplicate by topic similarity
            category_trends = self._deduplicate_trends(category_trends)

            all_trends[category] = category_trends[:max_results_per_category]

        logger.info(f"Discovered {sum(len(t) for t in all_trends.values())} total trends")
        return all_trends

    def _search_trends(
        self,
        query: str,
        category: str,
        max_results: int = 5,
        max_age_days: int = 7,
        force_refresh: bool = False
    ) -> List[Dict]:
        """Search for trends using Tavily API

        Args:
            query: Search query
            category: Trend category
            max_results: Maximum results to return
            max_age_days: Maximum age of content in days
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of trend dictionaries
        """
        try:
            # Check cache first (unless force_refresh is True)
            if not force_refresh:
                cached_trends = self._get_cached_trends(query, max_age_days)
                if cached_trends:
                    logger.info(f"Using {len(cached_trends)} cached trends for: {query}")
                    return cached_trends
            else:
                logger.info(f"Force refresh: bypassing cache for query: {query}")

            # Search Tavily
            response = self.client.search(
                query=query,
                search_depth="advanced",
                topic="news",
                max_results=max_results,
                max_age_days=max_age_days
            )

            trends = []
            if 'results' in response:
                for result in response['results']:
                    trend = {
                        'topic': result.get('title', ''),
                        'summary': result.get('content', ''),
                        'url': result.get('url', ''),
                        'published_date': result.get('published_date'),
                        'relevance_score': result.get('score', 0.5),
                        'category': category,
                        'search_query': query
                    }

                    # Calculate custom relevance score
                    trend['relevance_score'] = self._calculate_relevance(trend)

                    trends.append(trend)

                    # Cache trend
                    self._cache_trend(trend, max_age_days)

            logger.info(f"Found {len(trends)} trends for query: {query}")
            return trends

        except Exception as e:
            logger.error(f"Trend search failed for '{query}': {str(e)}")
            return []

    def _calculate_relevance(self, trend: Dict) -> float:
        """Calculate relevance score for CS/AI PhD students

        Args:
            trend: Trend dictionary

        Returns:
            Relevance score (0-1)
        """
        score = trend.get('relevance_score', 0.5)

        # Boost for research-relevant keywords
        research_keywords = [
            'paper', 'research', 'study', 'benchmark', 'arxiv',
            'model', 'training', 'architecture', 'performance'
        ]

        # Boost for job-seeking keywords
        job_keywords = [
            'hiring', 'jobs', 'career', 'opportunities', 'recruiting',
            'interview', 'salary', 'skills'
        ]

        # Boost for practical tools
        tool_keywords = [
            'framework', 'library', 'api', 'tutorial', 'guide',
            'implementation', 'code', 'github'
        ]

        text = f"{trend.get('topic', '')} {trend.get('summary', '')}".lower()

        # Count keyword matches
        research_count = sum(1 for kw in research_keywords if kw in text)
        job_count = sum(1 for kw in job_keywords if kw in text)
        tool_count = sum(1 for kw in tool_keywords if kw in text)

        # Boost score based on keyword matches
        if research_count >= 2:
            score += 0.2
        if job_count >= 1:
            score += 0.15
        if tool_count >= 1:
            score += 0.15

        # Cap at 1.0
        return min(score, 1.0)

    def _deduplicate_trends(self, trends: List[Dict]) -> List[Dict]:
        """Remove duplicate or very similar trends

        Args:
            trends: List of trend dictionaries

        Returns:
            Deduplicated list
        """
        if not trends:
            return []

        unique_trends = []
        seen_topics = set()

        for trend in trends:
            # Extract key terms from topic (words > 3 chars)
            topic_lower = trend.get('topic', '').lower()
            key_terms = frozenset(word for word in topic_lower.split() if len(word) > 3)

            # Check for significant overlap with seen topics
            is_duplicate = False
            for seen in seen_topics:
                overlap = len(key_terms & seen)
                # Consider duplicate if 50%+ overlap or 2+ shared key terms
                if overlap >= 2 or (len(key_terms) > 0 and overlap / len(key_terms) >= 0.5):
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_trends.append(trend)
                seen_topics.add(key_terms)

        logger.info(f"Deduplicated {len(trends)} -> {len(unique_trends)} trends")
        return unique_trends

    def _cache_trend(self, trend: Dict, expire_days: int = 7):
        """Cache trend in database

        Args:
            trend: Trend dictionary
            expire_days: Days until expiration
        """
        try:
            session = self.db_manager.get_session()

            expires_at = datetime.utcnow() + timedelta(days=expire_days)

            cached_trend = TrendingTopic(
                topic=trend['topic'],
                category=trend.get('category', 'general'),
                search_query=trend.get('search_query', ''),
                source_urls=[trend.get('url', '')],
                summary=trend.get('summary', ''),
                relevance_score=trend.get('relevance_score', 0.5),
                discovered_at=datetime.utcnow(),
                expires_at=expires_at,
                times_used=0,
                posts_generated=0
            )

            session.add(cached_trend)
            session.commit()
            session.close()

        except Exception as e:
            logger.error(f"Failed to cache trend: {str(e)}")

    def _get_cached_trends(
        self,
        query: str,
        max_age_days: int = 7
    ) -> List[Dict]:
        """Get cached trends from database

        Args:
            query: Search query
            max_age_days: Maximum age in days

        Returns:
            List of cached trend dictionaries
        """
        try:
            session = self.db_manager.get_session()

            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)

            cached = session.query(TrendingTopic).filter(
                TrendingTopic.search_query == query,
                TrendingTopic.discovered_at >= cutoff_date,
                TrendingTopic.expires_at > datetime.utcnow()
            ).all()

            trends = []
            for item in cached:
                trends.append({
                    'topic': item.topic,
                    'summary': item.summary,
                    'url': item.source_urls[0] if item.source_urls else '',
                    'relevance_score': item.relevance_score,
                    'category': item.category,
                    'search_query': item.search_query,
                    'cached': True
                })

            session.close()
            return trends

        except Exception as e:
            logger.error(f"Failed to retrieve cached trends: {str(e)}")
            return []

    def connect_trend_to_projects(
        self,
        trend: Dict,
        user_projects: List[str],
        research_area: str
    ) -> Dict:
        """Find connections between trend and user's work

        Args:
            trend: Trend dictionary
            user_projects: List of user's projects
            research_area: User's research area

        Returns:
            Dict with connection insights
        """
        # Extract key concepts from trend
        trend_text = f"{trend.get('topic', '')} {trend.get('summary', '')}".lower()

        # Extract key concepts from user's context
        user_context = f"{research_area} {' '.join(user_projects)}".lower()

        # Find overlapping concepts
        trend_words = set(word for word in trend_text.split() if len(word) > 4)
        user_words = set(word for word in user_context.split() if len(word) > 4)

        overlapping = trend_words & user_words

        # Determine connection strength
        connection_strength = len(overlapping) / max(len(trend_words), 1)

        # Generate connection angle
        if connection_strength >= 0.3:
            angle = "high_relevance"
            insight = f"Directly relevant to your work in {research_area}"
        elif connection_strength >= 0.1:
            angle = "moderate_relevance"
            insight = f"Potentially applicable to your {research_area} projects"
        else:
            angle = "industry_awareness"
            insight = "Important for staying aware of industry trends"

        return {
            'trend': trend,
            'connection_strength': connection_strength,
            'connection_angle': angle,
            'insight': insight,
            'overlapping_concepts': list(overlapping),
            'suggested_approach': self._suggest_content_approach(angle)
        }

    def _suggest_content_approach(self, angle: str) -> str:
        """Suggest how to frame content based on connection angle"""
        approaches = {
            'high_relevance': "Share how this relates to your current work and what you're learning",
            'moderate_relevance': "Discuss potential applications and what you're curious about",
            'industry_awareness': "Share your perspective as a student/researcher entering the field"
        }
        return approaches.get(angle, "Share your honest thoughts and questions")

    def get_best_trends_for_user(
        self,
        user_research_area: str,
        user_projects: List[str],
        num_trends: int = 5,
        force_refresh: bool = False
    ) -> List[Dict]:
        """Get most relevant trends for a specific user

        Args:
            user_research_area: User's research focus
            user_projects: List of user's projects
            num_trends: Number of trends to return
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of trends with connection analysis
        """
        # Discover trends across all categories
        all_trends_by_category = self.discover_weekly_trends(force_refresh=force_refresh)

        # Flatten to single list
        all_trends = []
        for category_trends in all_trends_by_category.values():
            all_trends.extend(category_trends)

        # Analyze connections for each trend
        trends_with_connections = []
        for trend in all_trends:
            connection = self.connect_trend_to_projects(
                trend, user_projects, user_research_area
            )
            trends_with_connections.append(connection)

        # Sort by connection strength
        trends_with_connections.sort(
            key=lambda x: x['connection_strength'],
            reverse=True
        )

        return trends_with_connections[:num_trends]
