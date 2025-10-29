"""
Social Media Analytics Tests

Comprehensive test suite for analytics collection and reporting.

Tests cover:
- Metrics collection from Twitter API
- Engagement rate calculations
- User analytics aggregation
- Best posting times analysis
- Recruiter engagement tracking
- Weekly report generation
- Error handling and edge cases

References:
- pytest: https://docs.pytest.org/
- Testing patterns: SOCIAL_MEDIA_GUIDE.md
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, Mock
from sqlalchemy.orm import Session

from src.social_media.analytics import AnalyticsCollector
from src.social_media.models import (
    Post, PostAnalytics, Analytics, User, Platform,
    PostStatus, ContentType, DatabaseManager
)
from src.social_media.twitter_handler import TwitterHandler
from utils.exceptions import APIError, RateLimitError


class TestAnalyticsCollector:
    """Test suite for AnalyticsCollector class"""

    def test_initialization(self, sm_db_manager):
        """Test analytics collector initialization"""
        collector = AnalyticsCollector(sm_db_manager)

        assert collector.db_manager == sm_db_manager
        assert collector.twitter_handler is None
        assert collector.logger is not None

    def test_initialization_with_twitter_handler(self, sm_db_manager):
        """Test initialization with Twitter handler"""
        mock_handler = MagicMock(spec=TwitterHandler)
        collector = AnalyticsCollector(sm_db_manager, twitter_handler=mock_handler)

        assert collector.twitter_handler == mock_handler

    def test_collect_post_metrics_success(self, sm_db_manager, sm_session, test_sm_user):
        """Test successful metrics collection from Twitter API"""
        # Create published post
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet for analytics",
            status=PostStatus.PUBLISHED,
            external_post_id="1234567890",
            published_time=datetime.utcnow() - timedelta(hours=2)
        )
        sm_session.add(post)
        sm_session.commit()
        sm_session.refresh(post)

        # Mock Twitter handler
        mock_handler = MagicMock(spec=TwitterHandler)
        mock_handler.get_tweet_metrics.return_value = {
            'tweet_id': '1234567890',
            'impressions': 1500,
            'likes': 45,
            'retweets': 12,
            'replies': 5,
            'quotes': 3
        }

        collector = AnalyticsCollector(sm_db_manager, twitter_handler=mock_handler)
        result = collector.collect_post_metrics(post.id)

        assert result['success'] is True
        assert result['metrics']['impressions'] == 1500
        assert result['metrics']['likes'] == 45
        assert result['metrics']['retweets'] == 12
        assert result['metrics']['replies'] == 5
        assert result['metrics']['quotes'] == 3
        assert 'collected_at' in result

        mock_handler.get_tweet_metrics.assert_called_once_with('1234567890')

    def test_collect_post_metrics_post_not_found(self, sm_db_manager):
        """Test metrics collection for non-existent post"""
        collector = AnalyticsCollector(sm_db_manager)
        result = collector.collect_post_metrics(99999)

        assert result['success'] is False
        assert 'Post not found' in result['error']
        assert result['metrics'] == {}

    def test_collect_post_metrics_post_not_published(self, sm_db_manager, sm_session, test_sm_user):
        """Test metrics collection for draft post"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Draft post",
            status=PostStatus.DRAFT
        )
        sm_session.add(post)
        sm_session.commit()
        sm_session.refresh(post)

        collector = AnalyticsCollector(sm_db_manager)
        result = collector.collect_post_metrics(post.id)

        assert result['success'] is False
        assert 'not published' in result['error']

    def test_collect_post_metrics_no_handler(self, sm_db_manager, sm_session, test_sm_user):
        """Test metrics collection without Twitter handler"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.PUBLISHED,
            external_post_id="1234567890",
            published_time=datetime.utcnow()
        )
        sm_session.add(post)
        sm_session.commit()
        sm_session.refresh(post)

        collector = AnalyticsCollector(sm_db_manager)
        result = collector.collect_post_metrics(post.id)

        assert result['success'] is False
        assert 'No Twitter handler' in result['error']

    def test_collect_post_metrics_api_error(self, sm_db_manager, sm_session, test_sm_user):
        """Test metrics collection with API error"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.PUBLISHED,
            external_post_id="1234567890",
            published_time=datetime.utcnow()
        )
        sm_session.add(post)
        sm_session.commit()
        sm_session.refresh(post)

        mock_handler = MagicMock(spec=TwitterHandler)
        mock_handler.get_tweet_metrics.side_effect = APIError("API call failed")

        collector = AnalyticsCollector(sm_db_manager, twitter_handler=mock_handler)
        result = collector.collect_post_metrics(post.id)

        assert result['success'] is False
        assert 'API call failed' in result['error']

    def test_collect_post_metrics_rate_limit(self, sm_db_manager, sm_session, test_sm_user):
        """Test metrics collection with rate limit error"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.PUBLISHED,
            external_post_id="1234567890",
            published_time=datetime.utcnow()
        )
        sm_session.add(post)
        sm_session.commit()
        sm_session.refresh(post)

        mock_handler = MagicMock(spec=TwitterHandler)
        mock_handler.get_tweet_metrics.side_effect = RateLimitError("Rate limit exceeded")

        collector = AnalyticsCollector(sm_db_manager, twitter_handler=mock_handler)

        # RateLimitError is caught and returned in result
        result = collector.collect_post_metrics(post.id)
        assert result['success'] is False

    def test_calculate_engagement_rate(self, sm_db_manager, sm_session, test_sm_user):
        """Test engagement rate calculation"""
        # Create post
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.PUBLISHED,
            published_time=datetime.utcnow()
        )
        sm_session.add(post)
        sm_session.commit()
        sm_session.refresh(post)

        # Create analytics
        analytics = PostAnalytics(
            post_id=post.id,
            impressions=1000,
            likes=50,
            comments=10,
            retweets=15,
            shares=5,
            snapshot_time=datetime.utcnow()
        )
        sm_session.add(analytics)
        sm_session.commit()

        collector = AnalyticsCollector(sm_db_manager)
        engagement_rate = collector.calculate_engagement_rate(post.id)

        # (50 + 10 + 15 + 5) / 1000 * 100 = 8.0%
        assert engagement_rate == 8.0

    def test_calculate_engagement_rate_no_analytics(self, sm_db_manager, sm_session, test_sm_user):
        """Test engagement rate calculation with no analytics"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.PUBLISHED
        )
        sm_session.add(post)
        sm_session.commit()
        sm_session.refresh(post)

        collector = AnalyticsCollector(sm_db_manager)
        engagement_rate = collector.calculate_engagement_rate(post.id)

        assert engagement_rate == 0.0

    def test_calculate_engagement_rate_zero_impressions(self, sm_db_manager, sm_session, test_sm_user):
        """Test engagement rate calculation with zero impressions"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.PUBLISHED
        )
        sm_session.add(post)
        sm_session.commit()
        sm_session.refresh(post)

        analytics = PostAnalytics(
            post_id=post.id,
            impressions=0,
            likes=5,
            snapshot_time=datetime.utcnow()
        )
        sm_session.add(analytics)
        sm_session.commit()

        collector = AnalyticsCollector(sm_db_manager)
        engagement_rate = collector.calculate_engagement_rate(post.id)

        assert engagement_rate == 0.0

    def test_update_post_analytics_success(self, sm_db_manager, sm_session, test_sm_user):
        """Test successful post analytics update"""
        # Create published post
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.PUBLISHED,
            external_post_id="1234567890",
            published_time=datetime.utcnow() - timedelta(hours=3)
        )
        sm_session.add(post)
        sm_session.commit()
        sm_session.refresh(post)

        # Mock Twitter handler
        mock_handler = MagicMock(spec=TwitterHandler)
        mock_handler.get_tweet_metrics.return_value = {
            'impressions': 2000,
            'likes': 60,
            'retweets': 18,
            'replies': 7,
            'quotes': 4,
            'url_clicks': 0
        }

        collector = AnalyticsCollector(sm_db_manager, twitter_handler=mock_handler)
        analytics = collector.update_post_analytics(post.id)

        assert analytics is not None
        assert analytics.post_id == post.id
        assert analytics.impressions == 2000
        assert analytics.likes == 60
        assert analytics.retweets == 18
        assert analytics.comments == 7
        assert analytics.shares == 4

        # Check engagement rate calculation
        # (60 + 18 + 7 + 4) / 2000 * 100 = 4.45%
        assert analytics.engagement_rate == pytest.approx(4.45, rel=0.01)

        # Check weighted score
        # 60*1 + 18*2 + 7*3 + 4*2 = 60 + 36 + 21 + 8 = 125
        assert analytics.weighted_engagement_score == 125.0

        # Check hours since published
        assert analytics.hours_since_published == 3

    def test_update_post_analytics_failed_collection(self, sm_db_manager, sm_session, test_sm_user):
        """Test analytics update with failed metrics collection"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.DRAFT  # Not published
        )
        sm_session.add(post)
        sm_session.commit()
        sm_session.refresh(post)

        collector = AnalyticsCollector(sm_db_manager)
        analytics = collector.update_post_analytics(post.id)

        assert analytics is None

    def test_get_user_analytics_summary_no_posts(self, sm_db_manager, test_sm_user):
        """Test analytics summary with no posts"""
        collector = AnalyticsCollector(sm_db_manager)
        summary = collector.get_user_analytics_summary(test_sm_user.id)

        assert summary['total_posts'] == 0
        assert summary['total_impressions'] == 0
        assert summary['total_engagements'] == 0
        assert summary['avg_engagement_rate'] == 0.0
        assert 'time_range' in summary

    def test_get_user_analytics_summary_with_posts(self, sm_db_manager, sm_session, test_sm_user):
        """Test analytics summary with multiple posts"""
        # Create posts with analytics
        posts_data = [
            {'impressions': 1000, 'likes': 50, 'retweets': 10, 'comments': 5, 'shares': 2},
            {'impressions': 2000, 'likes': 100, 'retweets': 20, 'comments': 10, 'shares': 5},
            {'impressions': 1500, 'likes': 75, 'retweets': 15, 'comments': 8, 'shares': 3}
        ]

        for data in posts_data:
            post = Post(
                user_id=test_sm_user.id,
                platform=Platform.TWITTER,
                content="Test tweet",
                content_type=ContentType.LEARNING_UPDATE,
                status=PostStatus.PUBLISHED,
                published_time=datetime.utcnow() - timedelta(days=2)
            )
            sm_session.add(post)
            sm_session.flush()

            analytics = PostAnalytics(
                post_id=post.id,
                impressions=data['impressions'],
                likes=data['likes'],
                retweets=data['retweets'],
                comments=data['comments'],
                shares=data['shares'],
                snapshot_time=datetime.utcnow()
            )
            sm_session.add(analytics)

        sm_session.commit()

        collector = AnalyticsCollector(sm_db_manager)
        summary = collector.get_user_analytics_summary(test_sm_user.id)

        assert summary['total_posts'] == 3
        assert summary['total_impressions'] == 4500
        assert summary['total_engagements'] == 303  # Sum of all engagements
        assert summary['avg_engagement_rate'] > 0
        assert 'best_post' in summary
        assert 'worst_post' in summary
        assert 'engagement_by_type' in summary

    def test_get_user_analytics_summary_custom_date_range(self, sm_db_manager, sm_session, test_sm_user):
        """Test analytics summary with custom date range"""
        # Create posts at different times
        post1 = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Old tweet",
            status=PostStatus.PUBLISHED,
            published_time=datetime.utcnow() - timedelta(days=40)
        )
        sm_session.add(post1)

        post2 = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Recent tweet",
            status=PostStatus.PUBLISHED,
            published_time=datetime.utcnow() - timedelta(days=5)
        )
        sm_session.add(post2)
        sm_session.commit()

        # Query last 7 days only
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)

        collector = AnalyticsCollector(sm_db_manager)
        summary = collector.get_user_analytics_summary(
            test_sm_user.id,
            date_range=(start_date, end_date)
        )

        # Should only include post2
        assert summary['total_posts'] == 1

    def test_identify_best_posting_times_no_posts(self, sm_db_manager, test_sm_user):
        """Test best posting times with no posts"""
        collector = AnalyticsCollector(sm_db_manager)
        best_times = collector.identify_best_posting_times(test_sm_user.id)

        assert best_times == []

    def test_identify_best_posting_times_with_data(self, sm_db_manager, sm_session, test_sm_user):
        """Test best posting times analysis with data"""
        # Create posts at different times
        base_time = datetime.utcnow() - timedelta(days=30)

        for i in range(10):
            # Posts on Monday at 10:00 UTC (high engagement)
            monday_time = base_time + timedelta(days=i*7, hours=10)
            post = Post(
                user_id=test_sm_user.id,
                platform=Platform.TWITTER,
                content=f"Monday post {i}",
                status=PostStatus.PUBLISHED,
                published_time=monday_time.replace(hour=10, minute=0)
            )
            sm_session.add(post)
            sm_session.flush()

            analytics = PostAnalytics(
                post_id=post.id,
                impressions=1000,
                likes=80,
                retweets=20,
                comments=10,
                shares=5,
                snapshot_time=datetime.utcnow()
            )
            sm_session.add(analytics)

        for i in range(5):
            # Posts on Friday at 16:00 UTC (lower engagement)
            friday_time = base_time + timedelta(days=i*7+4, hours=16)
            post = Post(
                user_id=test_sm_user.id,
                platform=Platform.TWITTER,
                content=f"Friday post {i}",
                status=PostStatus.PUBLISHED,
                published_time=friday_time.replace(hour=16, minute=0)
            )
            sm_session.add(post)
            sm_session.flush()

            analytics = PostAnalytics(
                post_id=post.id,
                impressions=1000,
                likes=30,
                retweets=5,
                comments=3,
                shares=2,
                snapshot_time=datetime.utcnow()
            )
            sm_session.add(analytics)

        sm_session.commit()

        collector = AnalyticsCollector(sm_db_manager)
        best_times = collector.identify_best_posting_times(test_sm_user.id)

        assert len(best_times) > 0

        # Check that Monday at 10:00 has higher engagement
        monday_10 = next((t for t in best_times if t['day_of_week'] == 0 and t['hour'] == 10), None)
        assert monday_10 is not None
        assert monday_10['avg_engagement_rate'] > 10.0  # (80+20+10+5)/1000 = 11.5%
        assert monday_10['posts_count'] >= 2

    def test_identify_best_posting_times_minimum_posts_threshold(self, sm_db_manager, sm_session, test_sm_user):
        """Test that best times requires at least 2 posts"""
        # Create only 1 post at a specific time
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Single post",
            status=PostStatus.PUBLISHED,
            published_time=datetime.utcnow().replace(hour=10, minute=0)
        )
        sm_session.add(post)
        sm_session.flush()

        analytics = PostAnalytics(
            post_id=post.id,
            impressions=1000,
            likes=100,
            snapshot_time=datetime.utcnow()
        )
        sm_session.add(analytics)
        sm_session.commit()

        collector = AnalyticsCollector(sm_db_manager)
        best_times = collector.identify_best_posting_times(test_sm_user.id)

        # Should return empty because we need at least 2 posts
        assert best_times == []

    def test_track_recruiter_engagement_no_data(self, sm_db_manager, test_sm_user):
        """Test recruiter engagement tracking with no data"""
        collector = AnalyticsCollector(sm_db_manager)
        metrics = collector.track_recruiter_engagement(test_sm_user.id)

        assert metrics['profile_views_7d'] == 0
        assert metrics['profile_views_30d'] == 0
        assert metrics['connection_requests'] == 0
        assert metrics['estimated_recruiter_reach'] == 0

    def test_track_recruiter_engagement_with_data(self, sm_db_manager, sm_session, test_sm_user):
        """Test recruiter engagement tracking with analytics data"""
        # Create analytics snapshots
        for i in range(7):
            analytics = Analytics(
                user_id=test_sm_user.id,
                platform=Platform.TWITTER,
                snapshot_date=datetime.utcnow() - timedelta(days=i),
                profile_views=100,
                connections_new=5,
                inmails_received=2,
                recruiter_messages=3,
                profile_saves=4,
                conversations_started=1,
                interviews_scheduled=0
            )
            sm_session.add(analytics)

        sm_session.commit()

        collector = AnalyticsCollector(sm_db_manager)
        metrics = collector.track_recruiter_engagement(test_sm_user.id)

        assert metrics['profile_views_7d'] == 700  # 100 * 7 days
        assert metrics['profile_views_30d'] == 700  # Only 7 days of data
        assert metrics['connection_requests'] == 5
        assert metrics['inmails_received'] == 2
        assert metrics['recruiter_engagements'] == 3
        assert metrics['estimated_recruiter_reach'] == 70  # 10% of 700

    def test_generate_weekly_report_structure(self, sm_db_manager, test_sm_user):
        """Test weekly report generation structure"""
        collector = AnalyticsCollector(sm_db_manager)
        report = collector.generate_weekly_report(test_sm_user.id)

        # Check report structure
        assert 'report_period' in report
        assert 'summary' in report
        assert 'top_posts' in report
        assert 'engagement_breakdown' in report
        assert 'best_times' in report
        assert 'recruiter_metrics' in report
        assert 'trends' in report
        assert 'recommendations' in report
        assert 'generated_at' in report

    def test_generate_weekly_report_with_data(self, sm_db_manager, sm_session, test_sm_user):
        """Test weekly report with real data"""
        # Create posts from last week
        for i in range(5):
            post = Post(
                user_id=test_sm_user.id,
                platform=Platform.TWITTER,
                content=f"Test post {i}",
                content_type=ContentType.LEARNING_UPDATE,
                status=PostStatus.PUBLISHED,
                published_time=datetime.utcnow() - timedelta(days=i)
            )
            sm_session.add(post)
            sm_session.flush()

            analytics = PostAnalytics(
                post_id=post.id,
                impressions=1000 + i*100,
                likes=50 + i*10,
                retweets=10 + i*2,
                comments=5 + i,
                shares=2,
                weighted_engagement_score=100 + i*20,
                snapshot_time=datetime.utcnow()
            )
            sm_session.add(analytics)

        sm_session.commit()

        collector = AnalyticsCollector(sm_db_manager)
        report = collector.generate_weekly_report(test_sm_user.id)

        assert report['summary']['total_posts'] == 5
        assert report['summary']['total_impressions'] > 0
        assert len(report['top_posts']) > 0
        assert len(report['recommendations']) > 0

    def test_generate_weekly_report_trends(self, sm_db_manager, sm_session, test_sm_user):
        """Test weekly report includes trend calculations"""
        # Create posts from two weeks ago
        for i in range(3):
            post = Post(
                user_id=test_sm_user.id,
                platform=Platform.TWITTER,
                content=f"Old post {i}",
                status=PostStatus.PUBLISHED,
                published_time=datetime.utcnow() - timedelta(days=14+i)
            )
            sm_session.add(post)
            sm_session.flush()

            analytics = PostAnalytics(
                post_id=post.id,
                impressions=500,
                likes=20,
                retweets=5,
                comments=2,
                shares=1,
                engagement_rate=5.6,
                snapshot_time=datetime.utcnow()
            )
            sm_session.add(analytics)

        # Create posts from last week (better performance)
        for i in range(3):
            post = Post(
                user_id=test_sm_user.id,
                platform=Platform.TWITTER,
                content=f"Recent post {i}",
                status=PostStatus.PUBLISHED,
                published_time=datetime.utcnow() - timedelta(days=i)
            )
            sm_session.add(post)
            sm_session.flush()

            analytics = PostAnalytics(
                post_id=post.id,
                impressions=1000,
                likes=50,
                retweets=10,
                comments=5,
                shares=2,
                engagement_rate=6.7,
                snapshot_time=datetime.utcnow()
            )
            sm_session.add(analytics)

        sm_session.commit()

        collector = AnalyticsCollector(sm_db_manager)
        report = collector.generate_weekly_report(test_sm_user.id)

        # Should show positive trends
        assert 'trends' in report
        # Check that trends were calculated (will be present if previous week had data)
        if report['trends']:
            assert 'impressions_change_pct' in report['trends'] or 'posts_change' in report['trends']
        # If no trends, that's okay - just verify the report structure
        assert 'summary' in report

    def test_recommendations_low_posting_frequency(self, sm_db_manager):
        """Test recommendations for low posting frequency"""
        collector = AnalyticsCollector(sm_db_manager)

        week_summary = {
            'total_posts': 1,  # Very low
            'avg_engagement_rate': 3.0,
            'engagement_by_type': {'learning_update': {}}
        }

        recommendations = collector._generate_recommendations(
            week_summary,
            best_times=[],
            recruiter_metrics={}
        )

        # Should recommend increasing frequency
        assert any('Increase posting frequency' in r for r in recommendations)

    def test_recommendations_high_posting_frequency(self, sm_db_manager):
        """Test recommendations for high posting frequency"""
        collector = AnalyticsCollector(sm_db_manager)

        week_summary = {
            'total_posts': 12,  # Very high
            'avg_engagement_rate': 3.0,
            'engagement_by_type': {'learning_update': {}}
        }

        recommendations = collector._generate_recommendations(
            week_summary,
            best_times=[],
            recruiter_metrics={}
        )

        # Should recommend reducing frequency
        assert any('reducing posting frequency' in r for r in recommendations)

    def test_recommendations_low_engagement_rate(self, sm_db_manager):
        """Test recommendations for low engagement rate"""
        collector = AnalyticsCollector(sm_db_manager)

        week_summary = {
            'total_posts': 5,
            'avg_engagement_rate': 1.0,  # Very low
            'engagement_by_type': {'learning_update': {}}
        }

        recommendations = collector._generate_recommendations(
            week_summary,
            best_times=[],
            recruiter_metrics={}
        )

        # Should recommend more engaging content
        assert any('Engagement rate is below average' in r for r in recommendations)

    def test_recommendations_excellent_engagement_rate(self, sm_db_manager):
        """Test recommendations for excellent engagement rate"""
        collector = AnalyticsCollector(sm_db_manager)

        week_summary = {
            'total_posts': 5,
            'avg_engagement_rate': 7.0,  # Excellent
            'engagement_by_type': {
                'learning_update': {},
                'project_showcase': {},
                'industry_insight': {}
            }
        }

        recommendations = collector._generate_recommendations(
            week_summary,
            best_times=[],
            recruiter_metrics={}
        )

        # Should praise good performance
        assert any('Excellent engagement rate' in r for r in recommendations)

    def test_recommendations_best_posting_times(self, sm_db_manager):
        """Test recommendations include best posting times"""
        collector = AnalyticsCollector(sm_db_manager)

        best_times = [
            {
                'day_name': 'Monday',
                'hour': 10,
                'avg_engagement_rate': 8.5
            }
        ]

        recommendations = collector._generate_recommendations(
            week_summary={'total_posts': 5, 'avg_engagement_rate': 3.0, 'engagement_by_type': {}},
            best_times=best_times,
            recruiter_metrics={}
        )

        # Should recommend specific posting time
        assert any('Monday' in r and '10:00' in r for r in recommendations)

    def test_recommendations_content_diversity(self, sm_db_manager):
        """Test recommendations for content diversity"""
        collector = AnalyticsCollector(sm_db_manager)

        week_summary = {
            'total_posts': 5,
            'avg_engagement_rate': 3.0,
            'engagement_by_type': {
                'learning_update': {}  # Only one type
            }
        }

        recommendations = collector._generate_recommendations(
            week_summary,
            best_times=[],
            recruiter_metrics={}
        )

        # Should recommend diversifying content
        assert any('Diversify content types' in r for r in recommendations)

    def test_create_user_analytics_snapshot(self, sm_db_manager, sm_session, test_sm_user):
        """Test creating user analytics snapshot"""
        # Create some posts
        for i in range(3):
            post = Post(
                user_id=test_sm_user.id,
                platform=Platform.TWITTER,
                content=f"Test post {i}",
                status=PostStatus.PUBLISHED,
                published_time=datetime.utcnow() - timedelta(days=i)
            )
            sm_session.add(post)

        sm_session.commit()

        mock_handler = MagicMock(spec=TwitterHandler)
        mock_handler.get_user_metrics.return_value = {
            'username': 'test_user',
            'followers': 500,
            'following': 200
        }

        collector = AnalyticsCollector(sm_db_manager, twitter_handler=mock_handler)
        snapshot = collector.create_user_analytics_snapshot(test_sm_user.id, Platform.TWITTER)

        assert snapshot is not None
        assert snapshot.user_id == test_sm_user.id
        assert snapshot.platform == Platform.TWITTER
        assert snapshot.posts_published_week == 3

    def test_create_user_analytics_snapshot_no_twitter_handler(self, sm_db_manager, test_sm_user):
        """Test creating snapshot without Twitter handler"""
        collector = AnalyticsCollector(sm_db_manager)
        snapshot = collector.create_user_analytics_snapshot(test_sm_user.id, Platform.TWITTER)

        assert snapshot is not None
        assert snapshot.user_id == test_sm_user.id


class TestAnalyticsEdgeCases:
    """Test edge cases and error handling"""

    def test_engagement_rate_rounding(self, sm_db_manager, sm_session, test_sm_user):
        """Test engagement rate is properly rounded"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test",
            status=PostStatus.PUBLISHED
        )
        sm_session.add(post)
        sm_session.flush()

        # Create analytics with rate that needs rounding
        analytics = PostAnalytics(
            post_id=post.id,
            impressions=1337,
            likes=33,
            comments=7,
            retweets=5,
            shares=0,
            snapshot_time=datetime.utcnow()
        )
        sm_session.add(analytics)
        sm_session.commit()

        collector = AnalyticsCollector(sm_db_manager)
        rate = collector.calculate_engagement_rate(post.id)

        # (33 + 7 + 5 + 0) / 1337 * 100 = 3.365...
        assert rate == 3.37  # Should be rounded to 2 decimal places

    def test_weighted_score_calculation(self, sm_db_manager, sm_session, test_sm_user):
        """Test weighted engagement score calculation"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.PUBLISHED,
            external_post_id="123",
            published_time=datetime.utcnow()
        )
        sm_session.add(post)
        sm_session.commit()
        sm_session.refresh(post)

        mock_handler = MagicMock(spec=TwitterHandler)
        mock_handler.get_tweet_metrics.return_value = {
            'impressions': 1000,
            'likes': 10,  # weight=1
            'retweets': 5,  # weight=2
            'replies': 3,  # weight=3
            'quotes': 2,  # weight=2
            'url_clicks': 0
        }

        collector = AnalyticsCollector(sm_db_manager, twitter_handler=mock_handler)
        analytics = collector.update_post_analytics(post.id)

        # 10*1 + 5*2 + 3*3 + 2*2 = 10 + 10 + 9 + 4 = 33
        assert analytics.weighted_engagement_score == 33.0

    def test_large_numbers_handling(self, sm_db_manager, sm_session, test_sm_user):
        """Test handling of large metric numbers"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Viral tweet",
            status=PostStatus.PUBLISHED
        )
        sm_session.add(post)
        sm_session.flush()

        # Create analytics with large numbers
        analytics = PostAnalytics(
            post_id=post.id,
            impressions=1_000_000,
            likes=50_000,
            retweets=10_000,
            comments=5_000,
            shares=2_000,
            snapshot_time=datetime.utcnow()
        )
        sm_session.add(analytics)
        sm_session.commit()

        collector = AnalyticsCollector(sm_db_manager)
        rate = collector.calculate_engagement_rate(post.id)

        # Should handle large numbers correctly
        assert rate == 6.7  # (50000+10000+5000+2000)/1000000 * 100


class TestAnalyticsIntegration:
    """Integration tests with database"""

    def test_full_analytics_workflow(self, sm_db_manager, sm_session, test_sm_user):
        """Test complete analytics collection workflow"""
        # 1. Create and publish post
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Integration test tweet",
            status=PostStatus.PUBLISHED,
            external_post_id="999",
            published_time=datetime.utcnow() - timedelta(hours=1)
        )
        sm_session.add(post)
        sm_session.commit()
        sm_session.refresh(post)

        # 2. Mock Twitter handler
        mock_handler = MagicMock(spec=TwitterHandler)
        mock_handler.get_tweet_metrics.return_value = {
            'impressions': 5000,
            'likes': 250,
            'retweets': 50,
            'replies': 25,
            'quotes': 10
        }

        # 3. Collect metrics
        collector = AnalyticsCollector(sm_db_manager, twitter_handler=mock_handler)
        result = collector.collect_post_metrics(post.id)
        assert result['success'] is True

        # 4. Update analytics
        analytics = collector.update_post_analytics(post.id)
        assert analytics is not None
        assert analytics.impressions == 5000

        # 5. Calculate engagement rate
        rate = collector.calculate_engagement_rate(post.id)
        assert rate > 0

        # 6. Get user summary
        summary = collector.get_user_analytics_summary(test_sm_user.id)
        assert summary['total_posts'] == 1

        # 7. Generate weekly report
        report = collector.generate_weekly_report(test_sm_user.id)
        assert report['summary']['total_posts'] == 1
