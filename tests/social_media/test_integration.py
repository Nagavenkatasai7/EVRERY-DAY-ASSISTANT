"""
End-to-End Integration Tests
Tests complete workflows across all components

Coverage targets:
- Complete content generation and posting workflow
- Trend discovery to content creation pipeline
- User onboarding and first post workflow
- Multi-platform posting workflow
- Analytics tracking workflow
- A/B testing workflow
- Error recovery and retry workflows
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from src.social_media.models import (
    User, Post, PostStatus, Platform, ContentType,
    OAuthToken, PostAnalytics, TrendingTopic,
    DatabaseManager, TokenEncryption
)
from src.social_media.twitter_handler import TwitterHandler
from src.social_media.content_generator import ContentGenerator
from src.social_media.trend_discovery import TrendDiscovery
from src.social_media.scheduler import PostScheduler


# ==================== Complete Workflow Tests ====================

@pytest.mark.integration
class TestCompleteWorkflows:
    """Test end-to-end workflows"""

    def test_user_onboarding_workflow(self, sm_db_manager, sm_session, sm_encryption_key):
        """Test complete user onboarding workflow"""
        encryptor = TokenEncryption()

        # Step 1: Create user
        user = User(
            username="new_user",
            email="newuser@example.com",
            full_name="New User",
            research_area="AI and Machine Learning",
            current_projects=["Research Project 1"],
            unique_perspective="Bridging theory and practice"
        )
        sm_session.add(user)
        sm_session.commit()

        # Step 2: Add OAuth tokens
        twitter_token = OAuthToken(
            user_id=user.id,
            platform=Platform.TWITTER,
            access_token_encrypted=encryptor.encrypt("twitter_access"),
            token_secret_encrypted=encryptor.encrypt("twitter_secret")
        )
        sm_session.add(twitter_token)
        sm_session.commit()

        # Step 3: Verify user setup complete
        assert user.id is not None
        assert len(user.oauth_tokens) == 1
        assert user.oauth_tokens[0].platform == Platform.TWITTER

    def test_content_generation_and_posting_workflow(self, mock_anthropic, mock_tweepy,
                                                     sm_db_manager, sm_session,
                                                     test_sm_user, test_twitter_token):
        """Test complete content generation and posting workflow"""
        # Step 1: Generate content
        generator = ContentGenerator(model_mode='api')

        content_result = generator.generate_project_showcase(
            project_name="RAG Chatbot",
            project_description="AI chatbot with RAG",
            technical_details="Python, LangChain, FAISS",
            results_metrics="98% accuracy",
            platform=Platform.TWITTER
        )

        assert content_result['content'] is not None
        assert content_result['ai_generated'] is True

        # Step 2: Check AI detection
        detection = generator.check_ai_detection_score(content_result['content'])

        # Step 3: Humanize if needed
        if detection['risk_level'] == 'HIGH':
            content_result['content'] = generator._humanize_content(content_result['content'])
            content_result['human_edited'] = True

        # Step 4: Create post in database
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content=content_result['content'],
            content_type=content_result['content_type'],
            status=PostStatus.DRAFT,
            ai_generated=True,
            ai_temperature=content_result['temperature'],
            human_edited=content_result.get('human_edited', False)
        )
        sm_session.add(post)
        sm_session.commit()

        # Step 5: Post to Twitter
        with patch.dict('os.environ', {
            'TWITTER_API_KEY': 'test_key',
            'TWITTER_API_SECRET': 'test_secret'
        }):
            handler = TwitterHandler(
                api_key="test_key",
                api_secret="test_secret",
                access_token="test_token",
                access_secret="test_secret",
                dry_run=False
            )

            result = handler.create_tweet(post.content)

        # Step 6: Update post status
        if result['success']:
            post.status = PostStatus.PUBLISHED
            post.published_time = result['created_at']
            post.external_post_id = result['tweet_id']
            post.external_url = result['url']
            sm_session.commit()

        # Verify complete workflow
        assert post.status == PostStatus.PUBLISHED
        assert post.external_post_id is not None

    def test_trend_to_content_workflow(self, mock_tavily, mock_anthropic,
                                      sm_db_manager, sm_session, test_sm_user):
        """Test trend discovery to content generation workflow"""
        # Step 1: Discover trends
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )

        trends = discovery.get_best_trends_for_user(
            user_research_area="AI and RAG systems",
            user_projects=["Research Assistant", "RAG Chatbot"],
            num_trends=3
        )

        assert len(trends) > 0

        # Step 2: Select a trend
        selected_trend = trends[0]

        # Step 3: Generate content about the trend
        generator = ContentGenerator(model_mode='api')

        content_result = generator.generate_trend_commentary(
            trend_topic=selected_trend['trend']['topic'],
            trend_summary=selected_trend['trend']['summary'],
            user_projects=["Research Assistant", "RAG Chatbot"],
            personal_angle=selected_trend['insight'],
            platform=Platform.TWITTER
        )

        assert content_result['content'] is not None
        assert content_result['content_type'] == ContentType.INDUSTRY_INSIGHT

        # Step 4: Create post
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content=content_result['content'],
            content_type=content_result['content_type'],
            status=PostStatus.DRAFT,
            ai_generated=True
        )
        sm_session.add(post)
        sm_session.commit()

        # Step 5: Update trend usage
        # (In real implementation, would update TrendingTopic.times_used)

        assert post.id is not None

    @pytest.mark.asyncio
    async def test_scheduled_posting_workflow(self, mock_tweepy, sm_db_manager,
                                             sm_session, test_sm_user, test_twitter_token):
        """Test complete scheduled posting workflow"""
        # Step 1: Create post
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Scheduled integration test",
            status=PostStatus.DRAFT
        )
        sm_session.add(post)
        sm_session.commit()

        # Step 2: Schedule post
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        scheduled_time = datetime.utcnow() + timedelta(seconds=1)
        job_id = scheduler.schedule_post(post.id, scheduled_time, test_sm_user.id)

        assert job_id is not None

        # Step 3: Verify scheduled
        scheduled_posts = scheduler.get_scheduled_posts(test_sm_user.id)
        assert any(p['post_id'] == post.id for p in scheduled_posts)

        # Step 4: Execute post (simulate scheduler execution)
        with patch.dict('os.environ', {
            'TWITTER_API_KEY': 'test_key',
            'TWITTER_API_SECRET': 'test_secret'
        }):
            await scheduler._execute_post(post.id, test_sm_user.id)

        # Step 5: Verify published
        sm_session.refresh(post)
        assert post.status == PostStatus.PUBLISHED

        scheduler.shutdown()

    def test_analytics_tracking_workflow(self, mock_tweepy, sm_db_manager,
                                         sm_session, test_sm_user):
        """Test analytics tracking workflow"""
        # Step 1: Create and publish post
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test analytics",
            status=PostStatus.PUBLISHED,
            published_time=datetime.utcnow(),
            external_post_id="1234567890"
        )
        sm_session.add(post)
        sm_session.commit()

        # Step 2: Fetch metrics from Twitter
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_secret"
        )

        metrics = handler.get_tweet_metrics(post.external_post_id)

        # Step 3: Store analytics
        analytics = PostAnalytics(
            post_id=post.id,
            impressions=metrics.get('impressions', 0),
            likes=metrics.get('likes', 0),
            retweets=metrics.get('retweets', 0),
            comments=metrics.get('comments', 0),
            hours_since_published=1
        )

        # Calculate engagement rate
        if analytics.impressions > 0:
            analytics.engagement_rate = (
                (analytics.likes + analytics.retweets + analytics.comments) /
                analytics.impressions
            )

        sm_session.add(analytics)
        sm_session.commit()

        # Verify analytics stored
        assert len(post.analytics) == 1
        assert post.analytics[0].likes > 0


# ==================== Multi-Platform Workflows ====================

@pytest.mark.integration
class TestMultiPlatformWorkflows:
    """Test workflows across multiple platforms"""

    def test_cross_platform_content_adaptation(self, mock_anthropic, sm_db_manager,
                                               sm_session, test_sm_user):
        """Test adapting content for different platforms"""
        generator = ContentGenerator(model_mode='api')

        # Generate for Twitter
        twitter_content = generator.generate_project_showcase(
            project_name="Test Project",
            project_description="Test description",
            technical_details="Python, AI",
            results_metrics="90% accuracy",
            platform=Platform.TWITTER
        )

        # Generate for LinkedIn
        linkedin_content = generator.generate_project_showcase(
            project_name="Test Project",
            project_description="Test description",
            technical_details="Python, AI",
            results_metrics="90% accuracy",
            platform=Platform.LINKEDIN
        )

        # Verify different lengths and styles
        assert len(twitter_content['content']) <= 280
        assert len(linkedin_content['content']) <= 1200
        assert twitter_content['platform'] == Platform.TWITTER
        assert linkedin_content['platform'] == Platform.LINKEDIN

    def test_user_with_multiple_platform_tokens(self, sm_db_manager, sm_session,
                                                test_sm_user, sm_encryption_key):
        """Test user managing multiple platform accounts"""
        encryptor = TokenEncryption()

        # Add Twitter token
        twitter_token = OAuthToken(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            access_token_encrypted=encryptor.encrypt("twitter_token"),
            token_secret_encrypted=encryptor.encrypt("twitter_secret")
        )
        sm_session.add(twitter_token)

        # Add LinkedIn token
        linkedin_token = OAuthToken(
            user_id=test_sm_user.id,
            platform=Platform.LINKEDIN,
            access_token_encrypted=encryptor.encrypt("linkedin_token")
        )
        sm_session.add(linkedin_token)
        sm_session.commit()

        # Verify user has tokens for both platforms
        tokens = sm_session.query(OAuthToken).filter(
            OAuthToken.user_id == test_sm_user.id
        ).all()

        platforms = [t.platform for t in tokens]
        assert Platform.TWITTER in platforms
        assert Platform.LINKEDIN in platforms


# ==================== A/B Testing Workflows ====================

@pytest.mark.integration
class TestABTestingWorkflows:
    """Test A/B testing workflows"""

    def test_variant_generation_and_testing(self, mock_anthropic, sm_db_manager,
                                           sm_session, test_sm_user):
        """Test generating and testing content variants"""
        generator = ContentGenerator(model_mode='api')

        # Generate variants
        params = {
            'project_name': 'Test Project',
            'project_description': 'Description',
            'technical_details': 'Tech',
            'results_metrics': 'Metrics',
            'platform': Platform.TWITTER
        }

        variants = generator.generate_multiple_variants(
            content_type='project_showcase',
            params=params,
            num_variants=3
        )

        # Create posts for each variant
        posts = []
        for variant in variants:
            post = Post(
                user_id=test_sm_user.id,
                platform=Platform.TWITTER,
                content=variant['content'],
                variant_group="test_experiment_1",
                test_variable="content_style",
                status=PostStatus.DRAFT
            )
            posts.append(post)

        sm_session.add_all(posts)
        sm_session.commit()

        # Verify variants created
        assert len(posts) == 3
        assert all(p.variant_group == "test_experiment_1" for p in posts)


# ==================== Error Recovery Workflows ====================

@pytest.mark.integration
class TestErrorRecoveryWorkflows:
    """Test error recovery and retry workflows"""

    @pytest.mark.asyncio
    async def test_post_failure_and_retry(self, mock_tweepy, sm_db_manager,
                                         sm_session, test_sm_user, test_twitter_token):
        """Test post failure and automatic retry"""
        # Mock initial failure, then success
        mock_tweepy.return_value.create_tweet.side_effect = [
            Exception("API Error"),
            MagicMock(data={'id': '123', 'text': 'Success'})
        ]

        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        # Create post
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test retry",
            status=PostStatus.SCHEDULED,
            max_retries=3
        )
        sm_session.add(post)
        sm_session.commit()

        # First attempt - will fail
        with patch.dict('os.environ', {
            'TWITTER_API_KEY': 'test_key',
            'TWITTER_API_SECRET': 'test_secret'
        }):
            await scheduler._execute_post(post.id, test_sm_user.id)

        sm_session.refresh(post)

        # Verify retry scheduled
        assert post.retry_count == 1
        assert post.status == PostStatus.SCHEDULED
        assert post.error_message is not None

        # Second attempt - will succeed
        with patch.dict('os.environ', {
            'TWITTER_API_KEY': 'test_key',
            'TWITTER_API_SECRET': 'test_secret'
        }):
            await scheduler._execute_post(post.id, test_sm_user.id)

        sm_session.refresh(post)

        # Verify eventually published
        assert post.status == PostStatus.PUBLISHED

        scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_permanent_failure_handling(self, mock_tweepy, sm_db_manager,
                                              sm_session, test_sm_user, test_twitter_token):
        """Test handling permanent failures after max retries"""
        mock_tweepy.return_value.create_tweet.side_effect = Exception("Permanent Error")

        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test permanent failure",
            status=PostStatus.SCHEDULED,
            retry_count=3,
            max_retries=3
        )
        sm_session.add(post)
        sm_session.commit()

        # Execute - should mark as failed
        with patch.dict('os.environ', {
            'TWITTER_API_KEY': 'test_key',
            'TWITTER_API_SECRET': 'test_secret'
        }):
            await scheduler._execute_post(post.id, test_sm_user.id)

        sm_session.refresh(post)

        # Verify marked as failed
        assert post.status == PostStatus.FAILED
        assert post.retry_count == 3


# ==================== Content Quality Workflows ====================

@pytest.mark.integration
class TestContentQualityWorkflows:
    """Test content quality assurance workflows"""

    def test_ai_detection_and_humanization(self, mock_anthropic, sm_db_manager,
                                           sm_session, test_sm_user, ai_red_flag_content):
        """Test detecting and fixing AI-generated content"""
        generator = ContentGenerator(model_mode='api')

        # Step 1: Check AI detection score
        detection = generator.check_ai_detection_score(ai_red_flag_content)

        assert detection['ai_detection_score'] > 50
        assert detection['risk_level'] in ['MEDIUM', 'HIGH']

        # Step 2: Humanize content
        humanized = generator._humanize_content(ai_red_flag_content)

        # Step 3: Re-check after humanization
        new_detection = generator.check_ai_detection_score(humanized)

        # Verify improvement
        assert new_detection['ai_detection_score'] < detection['ai_detection_score']

    def test_content_approval_workflow(self, mock_anthropic, sm_db_manager,
                                       sm_session, test_sm_user):
        """Test content review and approval workflow"""
        generator = ContentGenerator(model_mode='api')

        # Generate content
        content_result = generator.generate_learning_update(
            topic="RAG systems",
            key_insights=["Insight 1", "Insight 2"],
            practical_application="Applied to project",
            platform=Platform.TWITTER
        )

        # Create draft post
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content=content_result['content'],
            status=PostStatus.DRAFT,
            ai_generated=True
        )
        sm_session.add(post)
        sm_session.commit()

        # Simulate human review and edit
        post.content = "Edited: " + post.content[:250]
        post.human_edited = True
        sm_session.commit()

        # Approve for posting
        post.status = PostStatus.SCHEDULED
        post.scheduled_time = datetime.utcnow() + timedelta(hours=1)
        sm_session.commit()

        # Verify workflow
        assert post.human_edited is True
        assert post.status == PostStatus.SCHEDULED


# ==================== Performance and Scale Tests ====================

@pytest.mark.integration
class TestPerformanceWorkflows:
    """Test performance with larger data sets"""

    def test_bulk_post_creation(self, mock_anthropic, sm_db_manager,
                               sm_session, test_sm_user):
        """Test creating multiple posts efficiently"""
        generator = ContentGenerator(model_mode='api')

        posts = []
        for i in range(10):
            content_result = generator.generate_learning_update(
                topic=f"Topic {i}",
                key_insights=[f"Insight {i}"],
                practical_application="Applied",
                platform=Platform.TWITTER
            )

            post = Post(
                user_id=test_sm_user.id,
                platform=Platform.TWITTER,
                content=content_result['content'],
                content_type=content_result['content_type'],
                status=PostStatus.DRAFT
            )
            posts.append(post)

        # Bulk insert
        sm_session.add_all(posts)
        sm_session.commit()

        # Verify all created
        user_posts = sm_session.query(Post).filter(
            Post.user_id == test_sm_user.id
        ).all()

        assert len(user_posts) >= 10

    def test_trend_caching_performance(self, mock_tavily, sm_db_manager, sm_session):
        """Test trend caching improves performance"""
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
            # Cache the trend
            discovery._cache_trend(trends1[0], expire_days=7)

        # Second search - use cache
        cached_trends = discovery._get_cached_trends("AI research", max_age_days=7)

        # Verify caching works
        assert len(cached_trends) > 0


# ==================== Real-World Scenario Tests ====================

@pytest.mark.integration
class TestRealWorldScenarios:
    """Test realistic user scenarios"""

    def test_daily_posting_routine(self, mock_anthropic, mock_tweepy,
                                   sm_db_manager, sm_session, test_sm_user,
                                   test_twitter_token):
        """Test typical daily posting routine"""
        generator = ContentGenerator(model_mode='api')
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        # Morning: Generate project update
        morning_post_content = generator.generate_project_showcase(
            project_name="Daily Project",
            project_description="Daily progress",
            technical_details="Python",
            results_metrics="Progress made",
            platform=Platform.TWITTER
        )

        morning_post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content=morning_post_content['content'],
            status=PostStatus.DRAFT
        )
        sm_session.add(morning_post)
        sm_session.commit()

        # Schedule for 9 AM
        morning_time = datetime.utcnow() + timedelta(hours=1)
        scheduler.schedule_post(morning_post.id, morning_time, test_sm_user.id)

        # Afternoon: Generate learning update
        afternoon_post_content = generator.generate_learning_update(
            topic="Daily learning",
            key_insights=["New insight"],
            practical_application="Applied today",
            platform=Platform.TWITTER
        )

        afternoon_post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content=afternoon_post_content['content'],
            status=PostStatus.DRAFT
        )
        sm_session.add(afternoon_post)
        sm_session.commit()

        # Schedule for 2 PM
        afternoon_time = datetime.utcnow() + timedelta(hours=5)
        scheduler.schedule_post(afternoon_post.id, afternoon_time, test_sm_user.id)

        # Verify both scheduled
        scheduled = scheduler.get_scheduled_posts(test_sm_user.id)
        assert len(scheduled) >= 2

        scheduler.shutdown()

    def test_trend_based_content_strategy(self, mock_tavily, mock_anthropic,
                                          sm_db_manager, sm_session, test_sm_user):
        """Test weekly trend-based content strategy"""
        discovery = TrendDiscovery(
            api_key="test_key",
            db_manager=sm_db_manager
        )
        generator = ContentGenerator(model_mode='api')

        # Discover weekly trends
        trends = discovery.discover_weekly_trends(
            categories=['ai_research', 'tech_news'],
            max_results_per_category=3
        )

        # Generate content for top trends
        posts_created = 0
        for category, category_trends in trends.items():
            for trend in category_trends[:2]:  # Top 2 per category
                content_result = generator.generate_trend_commentary(
                    trend_topic=trend['topic'],
                    trend_summary=trend['summary'],
                    user_projects=["Research Assistant"],
                    personal_angle="Relevant to my work",
                    platform=Platform.TWITTER
                )

                post = Post(
                    user_id=test_sm_user.id,
                    platform=Platform.TWITTER,
                    content=content_result['content'],
                    content_type=content_result['content_type'],
                    status=PostStatus.DRAFT
                )
                sm_session.add(post)
                posts_created += 1

        sm_session.commit()

        # Verify content created from trends
        assert posts_created > 0
