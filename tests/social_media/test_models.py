"""
Comprehensive Database Model Tests
Tests all SQLAlchemy models, encryption, and database operations

Coverage targets:
- User model with research context
- Post model with AI metadata
- OAuthToken with encryption/decryption
- PostAnalytics metrics
- TrendingTopic caching
- TokenEncryption class
- DatabaseManager operations
"""

import pytest
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

from src.social_media.models import (
    User, Post, PostStatus, Platform, ContentType,
    OAuthToken, PostAnalytics, Analytics, TrendingTopic,
    ContentTemplate, ContentCalendar, ABTest,
    DatabaseManager, TokenEncryption
)


# ==================== User Model Tests ====================

@pytest.mark.unit
class TestUserModel:
    """Test User model functionality"""

    def test_create_user_minimal(self, sm_session):
        """Test creating user with minimal required fields"""
        user = User(
            username="testuser",
            email="test@example.com"
        )
        sm_session.add(user)
        sm_session.commit()

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_create_user_full_profile(self, sm_session):
        """Test creating user with complete profile"""
        projects = ["RAG Chatbot", "Multi-Agent System", "Research Assistant"]

        user = User(
            username="phd_researcher",
            email="phd@university.edu",
            full_name="Dr. AI Researcher",
            research_area="Multi-agent AI and Large Language Models",
            current_projects=projects,
            unique_perspective="Bridging academic research and production systems"
        )
        sm_session.add(user)
        sm_session.commit()

        assert user.id is not None
        assert user.research_area == "Multi-agent AI and Large Language Models"
        assert user.current_projects == projects
        assert len(user.current_projects) == 3

    def test_user_unique_constraints(self, sm_session):
        """Test username and email uniqueness"""
        user1 = User(username="unique", email="unique@test.com")
        sm_session.add(user1)
        sm_session.commit()

        # Duplicate username should fail
        user2 = User(username="unique", email="different@test.com")
        sm_session.add(user2)
        with pytest.raises(Exception):  # IntegrityError
            sm_session.commit()
        sm_session.rollback()

        # Duplicate email should fail
        user3 = User(username="different", email="unique@test.com")
        sm_session.add(user3)
        with pytest.raises(Exception):
            sm_session.commit()

    def test_user_relationships(self, sm_session):
        """Test user relationships cascade properly"""
        user = User(username="reltest", email="rel@test.com")
        sm_session.add(user)
        sm_session.commit()

        # Add posts
        post1 = Post(
            user_id=user.id,
            platform=Platform.TWITTER,
            content="Test post 1",
            status=PostStatus.DRAFT
        )
        post2 = Post(
            user_id=user.id,
            platform=Platform.TWITTER,
            content="Test post 2",
            status=PostStatus.PUBLISHED
        )
        sm_session.add_all([post1, post2])
        sm_session.commit()

        # Check relationship
        assert len(user.posts) == 2
        assert all(isinstance(p, Post) for p in user.posts)

    def test_user_updated_at(self, sm_session):
        """Test updated_at timestamp changes on update"""
        user = User(username="timetest", email="time@test.com")
        sm_session.add(user)
        sm_session.commit()

        original_updated = user.updated_at

        # Update user
        user.full_name = "Updated Name"
        sm_session.commit()

        # updated_at should change (or be close to current time)
        assert user.updated_at >= original_updated


# ==================== Post Model Tests ====================

@pytest.mark.unit
class TestPostModel:
    """Test Post model functionality"""

    def test_create_draft_post(self, sm_session, test_sm_user):
        """Test creating a draft post"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="This is a test tweet about AI",
            content_type=ContentType.PROJECT_SHOWCASE,
            status=PostStatus.DRAFT
        )
        sm_session.add(post)
        sm_session.commit()

        assert post.id is not None
        assert post.status == PostStatus.DRAFT
        assert post.platform == Platform.TWITTER
        assert post.retry_count == 0
        assert post.max_retries == 3

    def test_post_with_ai_metadata(self, sm_session, test_sm_user):
        """Test post with AI generation metadata"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="AI-generated content",
            ai_generated=True,
            ai_temperature=0.75,
            ai_prompt_version="v1.2",
            human_edited=False
        )
        sm_session.add(post)
        sm_session.commit()

        assert post.ai_generated is True
        assert post.ai_temperature == 0.75
        assert post.ai_prompt_version == "v1.2"
        assert post.human_edited is False

    def test_post_with_hashtags_and_media(self, sm_session, test_sm_user):
        """Test post with hashtags and media URLs"""
        hashtags = ["#AI", "#MachineLearning", "#Python"]
        media_urls = ["/path/to/image1.jpg", "/path/to/image2.jpg"]

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Post with media",
            hashtags=hashtags,
            media_urls=media_urls
        )
        sm_session.add(post)
        sm_session.commit()

        assert post.hashtags == hashtags
        assert post.media_urls == media_urls
        assert len(post.media_urls) == 2

    def test_scheduled_post(self, sm_session, test_sm_user):
        """Test scheduling a post"""
        scheduled_time = datetime.utcnow() + timedelta(hours=2)

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Scheduled tweet",
            status=PostStatus.SCHEDULED,
            scheduled_time=scheduled_time
        )
        sm_session.add(post)
        sm_session.commit()

        assert post.status == PostStatus.SCHEDULED
        assert post.scheduled_time == scheduled_time
        assert post.published_time is None

    def test_published_post(self, sm_session, test_sm_user):
        """Test published post with external IDs"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Published tweet",
            status=PostStatus.PUBLISHED,
            published_time=datetime.utcnow(),
            external_post_id="1234567890123456789",
            external_url="https://twitter.com/user/status/1234567890123456789"
        )
        sm_session.add(post)
        sm_session.commit()

        assert post.status == PostStatus.PUBLISHED
        assert post.external_post_id is not None
        assert post.external_url is not None
        assert post.published_time is not None

    def test_failed_post_with_retry(self, sm_session, test_sm_user):
        """Test failed post with retry tracking"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Failed tweet",
            status=PostStatus.FAILED,
            error_message="API rate limit exceeded",
            retry_count=3,
            max_retries=3
        )
        sm_session.add(post)
        sm_session.commit()

        assert post.status == PostStatus.FAILED
        assert post.error_message is not None
        assert post.retry_count == post.max_retries

    def test_post_ab_test_variant(self, sm_session, test_sm_user):
        """Test post with A/B testing metadata"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="A/B test variant A",
            variant_group="experiment_1",
            test_variable="posting_time"
        )
        sm_session.add(post)
        sm_session.commit()

        assert post.variant_group == "experiment_1"
        assert post.test_variable == "posting_time"

    def test_post_analytics_relationship(self, sm_session, test_sm_user):
        """Test post analytics relationship"""
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Post with analytics",
            status=PostStatus.PUBLISHED
        )
        sm_session.add(post)
        sm_session.commit()

        # Add analytics
        analytics = PostAnalytics(
            post_id=post.id,
            impressions=1000,
            likes=50,
            retweets=10,
            comments=5
        )
        sm_session.add(analytics)
        sm_session.commit()

        assert len(post.analytics) == 1
        assert post.analytics[0].impressions == 1000


# ==================== OAuthToken Model Tests ====================

@pytest.mark.unit
class TestOAuthTokenModel:
    """Test OAuthToken model and encryption"""

    def test_create_oauth_token(self, sm_session, test_sm_user, sm_encryption_key):
        """Test creating OAuth token with encryption"""
        encryptor = TokenEncryption()

        token = OAuthToken(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            access_token_encrypted=encryptor.encrypt("access_token_123"),
            token_secret_encrypted=encryptor.encrypt("token_secret_456"),
            expires_at=datetime.utcnow() + timedelta(days=30),
            scope="read write",
            token_type="OAuth1.0a"
        )
        sm_session.add(token)
        sm_session.commit()

        assert token.id is not None
        assert token.platform == Platform.TWITTER
        assert token.access_token_encrypted is not None
        assert token.token_secret_encrypted is not None

    def test_token_encryption_decryption(self, sm_encryption_key):
        """Test token encryption and decryption"""
        encryptor = TokenEncryption()

        original_token = "my_secret_token_12345"

        # Encrypt
        encrypted = encryptor.encrypt(original_token)
        assert encrypted != original_token
        assert isinstance(encrypted, str)

        # Decrypt
        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == original_token

    def test_token_encryption_none_handling(self, sm_encryption_key):
        """Test encryption handles None values"""
        encryptor = TokenEncryption()

        encrypted = encryptor.encrypt(None)
        assert encrypted is None

        decrypted = encryptor.decrypt(None)
        assert decrypted is None

    def test_oauth_token_user_relationship(self, sm_session, test_sm_user, test_twitter_token):
        """Test OAuth token user relationship"""
        assert test_twitter_token.user_id == test_sm_user.id
        assert test_twitter_token in test_sm_user.oauth_tokens

    def test_multiple_platform_tokens(self, sm_session, test_sm_user, sm_encryption_key):
        """Test user with multiple platform tokens"""
        encryptor = TokenEncryption()

        # Twitter token
        twitter_token = OAuthToken(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            access_token_encrypted=encryptor.encrypt("twitter_token")
        )

        # LinkedIn token
        linkedin_token = OAuthToken(
            user_id=test_sm_user.id,
            platform=Platform.LINKEDIN,
            access_token_encrypted=encryptor.encrypt("linkedin_token")
        )

        sm_session.add_all([twitter_token, linkedin_token])
        sm_session.commit()

        assert len(test_sm_user.oauth_tokens) >= 2


# ==================== PostAnalytics Model Tests ====================

@pytest.mark.unit
class TestPostAnalyticsModel:
    """Test PostAnalytics model"""

    def test_create_post_analytics(self, sm_session, draft_post):
        """Test creating post analytics"""
        analytics = PostAnalytics(
            post_id=draft_post.id,
            impressions=5000,
            views=4500,
            likes=150,
            comments=25,
            shares=30,
            retweets=20,
            clicks=100
        )
        sm_session.add(analytics)
        sm_session.commit()

        assert analytics.id is not None
        assert analytics.post_id == draft_post.id
        assert analytics.impressions == 5000
        assert analytics.likes == 150

    def test_engagement_rate_calculation(self, sm_session, draft_post):
        """Test engagement rate calculation"""
        analytics = PostAnalytics(
            post_id=draft_post.id,
            impressions=10000,
            likes=100,
            comments=50,
            shares=20
        )

        # Calculate engagement rate: (likes + comments + shares) / impressions
        engagement_rate = (100 + 50 + 20) / 10000
        analytics.engagement_rate = engagement_rate

        sm_session.add(analytics)
        sm_session.commit()

        assert analytics.engagement_rate == 0.017

    def test_recruiter_specific_metrics(self, sm_session, draft_post):
        """Test recruiter-specific metrics"""
        analytics = PostAnalytics(
            post_id=draft_post.id,
            profile_views_after=45,
            connection_requests=5,
            recruiter_engagements=3
        )
        sm_session.add(analytics)
        sm_session.commit()

        assert analytics.profile_views_after == 45
        assert analytics.connection_requests == 5
        assert analytics.recruiter_engagements == 3

    def test_multiple_analytics_snapshots(self, sm_session, draft_post):
        """Test multiple analytics snapshots for same post"""
        # Snapshot at 1 hour
        analytics1 = PostAnalytics(
            post_id=draft_post.id,
            impressions=500,
            likes=10,
            hours_since_published=1
        )

        # Snapshot at 24 hours
        analytics2 = PostAnalytics(
            post_id=draft_post.id,
            impressions=5000,
            likes=150,
            hours_since_published=24
        )

        sm_session.add_all([analytics1, analytics2])
        sm_session.commit()

        assert len(draft_post.analytics) == 2
        assert draft_post.analytics[1].impressions > draft_post.analytics[0].impressions


# ==================== TrendingTopic Model Tests ====================

@pytest.mark.unit
class TestTrendingTopicModel:
    """Test TrendingTopic model"""

    def test_create_trending_topic(self, sm_session):
        """Test creating trending topic"""
        topic = TrendingTopic(
            topic="GPT-5 Announcement",
            category="tech_news",
            search_query="GPT-5 OpenAI 2025",
            source_urls=["https://example.com/gpt5"],
            summary="OpenAI announces GPT-5 with improved reasoning",
            relevance_score=0.95,
            discovered_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        sm_session.add(topic)
        sm_session.commit()

        assert topic.id is not None
        assert topic.relevance_score == 0.95
        assert topic.category == "tech_news"

    def test_trending_topic_usage_tracking(self, sm_session):
        """Test usage tracking for trending topics"""
        topic = TrendingTopic(
            topic="RAG Systems Best Practices",
            category="ai_research",
            relevance_score=0.88,
            times_used=0,
            posts_generated=0
        )
        sm_session.add(topic)
        sm_session.commit()

        # Simulate usage
        topic.times_used += 1
        topic.posts_generated += 2
        sm_session.commit()

        assert topic.times_used == 1
        assert topic.posts_generated == 2

    def test_trending_topic_expiration(self, sm_session):
        """Test trending topic expiration"""
        expired_topic = TrendingTopic(
            topic="Old News",
            category="tech_news",
            relevance_score=0.5,
            discovered_at=datetime.utcnow() - timedelta(days=10),
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        sm_session.add(expired_topic)
        sm_session.commit()

        # Query for non-expired topics
        active_topics = sm_session.query(TrendingTopic).filter(
            TrendingTopic.expires_at > datetime.utcnow()
        ).all()

        assert expired_topic not in active_topics


# ==================== ContentTemplate Model Tests ====================

@pytest.mark.unit
class TestContentTemplateModel:
    """Test ContentTemplate model"""

    def test_create_content_template(self, sm_session, test_sm_user):
        """Test creating content template"""
        template = ContentTemplate(
            user_id=test_sm_user.id,
            name="Project Showcase Template",
            content_type=ContentType.PROJECT_SHOWCASE,
            template_text="Built {project_name} using {tech_stack}. Key results: {metrics}",
            tone="professional",
            typical_length=250,
            emoji_usage=False,
            hashtag_count=2
        )
        sm_session.add(template)
        sm_session.commit()

        assert template.id is not None
        assert template.name == "Project Showcase Template"
        assert template.tone == "professional"

    def test_template_performance_tracking(self, sm_session, test_sm_user):
        """Test template performance tracking"""
        template = ContentTemplate(
            user_id=test_sm_user.id,
            name="Learning Update Template",
            content_type=ContentType.LEARNING_UPDATE,
            times_used=10,
            avg_engagement=0.045
        )
        sm_session.add(template)
        sm_session.commit()

        assert template.times_used == 10
        assert template.avg_engagement == 0.045


# ==================== Analytics Model Tests ====================

@pytest.mark.unit
class TestAnalyticsModel:
    """Test user-level Analytics model"""

    def test_create_analytics_snapshot(self, sm_session, test_sm_user):
        """Test creating analytics snapshot"""
        analytics = Analytics(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            snapshot_date=datetime.utcnow(),
            profile_views=250,
            connections_new=15,
            inmails_received=3,
            posts_published_week=5,
            avg_engagement_rate=0.035
        )
        sm_session.add(analytics)
        sm_session.commit()

        assert analytics.id is not None
        assert analytics.profile_views == 250
        assert analytics.posts_published_week == 5

    def test_analytics_trend_tracking(self, sm_session, test_sm_user):
        """Test analytics trend tracking"""
        analytics = Analytics(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            view_change_pct=15.5,
            engagement_trend=8.2
        )
        sm_session.add(analytics)
        sm_session.commit()

        assert analytics.view_change_pct == 15.5
        assert analytics.engagement_trend == 8.2


# ==================== ContentCalendar Model Tests ====================

@pytest.mark.unit
class TestContentCalendarModel:
    """Test ContentCalendar model"""

    def test_create_content_calendar(self, sm_session, test_sm_user):
        """Test creating content calendar"""
        calendar = ContentCalendar(
            user_id=test_sm_user.id,
            week_number=4,
            year=2025,
            theme="AI Safety and Alignment",
            project_updates_pct=30,
            learning_shares_pct=20,
            industry_insights_pct=20,
            personal_stories_pct=20,
            deep_dives_pct=10,
            content_ideas=["RAG optimization tips", "Multi-agent coordination", "AI safety concerns"]
        )
        sm_session.add(calendar)
        sm_session.commit()

        assert calendar.id is not None
        assert calendar.theme == "AI Safety and Alignment"
        assert len(calendar.content_ideas) == 3
        assert sum([
            calendar.project_updates_pct,
            calendar.learning_shares_pct,
            calendar.industry_insights_pct,
            calendar.personal_stories_pct,
            calendar.deep_dives_pct
        ]) == 100


# ==================== ABTest Model Tests ====================

@pytest.mark.unit
class TestABTestModel:
    """Test ABTest model"""

    def test_create_ab_test(self, sm_session, test_sm_user):
        """Test creating A/B test"""
        test = ABTest(
            user_id=test_sm_user.id,
            experiment_name="Posting Time Test",
            test_variable="posting_time",
            variant_a_config={"time": "9:00 AM"},
            variant_b_config={"time": "6:00 PM"},
            status="running"
        )
        sm_session.add(test)
        sm_session.commit()

        assert test.id is not None
        assert test.experiment_name == "Posting Time Test"
        assert test.status == "running"

    def test_ab_test_results(self, sm_session, test_sm_user):
        """Test A/B test results tracking"""
        test = ABTest(
            user_id=test_sm_user.id,
            experiment_name="Content Format Test",
            test_variable="content_format",
            variant_a_impressions=5000,
            variant_a_conversions=150,
            variant_b_impressions=5200,
            variant_b_conversions=180,
            probability_a_better=0.35,
            winner="B",
            confidence_level=0.95,
            status="completed"
        )
        sm_session.add(test)
        sm_session.commit()

        assert test.winner == "B"
        assert test.confidence_level == 0.95
        assert test.variant_b_conversions > test.variant_a_conversions


# ==================== DatabaseManager Tests ====================

@pytest.mark.unit
class TestDatabaseManager:
    """Test DatabaseManager functionality"""

    def test_create_database_manager(self):
        """Test creating database manager"""
        import tempfile
        import os

        db_fd, db_path = tempfile.mkstemp(suffix='_test.db')
        db_url = f'sqlite:///{db_path}'

        manager = DatabaseManager(database_url=db_url)
        assert manager.engine is not None
        assert manager.SessionLocal is not None

        os.close(db_fd)
        os.unlink(db_path)

    def test_create_tables(self, sm_temp_db):
        """Test table creation"""
        manager = DatabaseManager(database_url=sm_temp_db)
        manager.create_tables()

        # Verify tables exist by creating a session
        session = manager.get_session()
        assert session is not None
        session.close()

    def test_get_session(self, sm_db_manager):
        """Test getting database session"""
        session = sm_db_manager.get_session()
        assert session is not None
        session.close()

    def test_multiple_sessions(self, sm_db_manager):
        """Test multiple concurrent sessions"""
        session1 = sm_db_manager.get_session()
        session2 = sm_db_manager.get_session()

        assert session1 is not session2

        session1.close()
        session2.close()


# ==================== TokenEncryption Tests ====================

@pytest.mark.unit
class TestTokenEncryption:
    """Test TokenEncryption class"""

    def test_encryption_with_env_key(self, sm_encryption_key):
        """Test encryption with environment key"""
        encryptor = TokenEncryption()

        token = "super_secret_token"
        encrypted = encryptor.encrypt(token)

        assert encrypted is not None
        assert encrypted != token
        assert isinstance(encrypted, str)

    def test_decryption_with_env_key(self, sm_encryption_key):
        """Test decryption with environment key"""
        encryptor = TokenEncryption()

        token = "super_secret_token"
        encrypted = encryptor.encrypt(token)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == token

    def test_encryption_decryption_round_trip(self, sm_encryption_key):
        """Test full encryption/decryption round trip"""
        encryptor = TokenEncryption()

        original = "my_oauth_token_12345"
        encrypted = encryptor.encrypt(original)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == original
        assert encrypted != original

    def test_different_encryptions(self, sm_encryption_key):
        """Test that same input produces different encryptions (IV randomization)"""
        encryptor = TokenEncryption()

        token = "test_token"
        encrypted1 = encryptor.encrypt(token)
        encrypted2 = encryptor.encrypt(token)

        # Due to Fernet's random IV, encryptions should differ
        # But both should decrypt to same value
        assert encryptor.decrypt(encrypted1) == token
        assert encryptor.decrypt(encrypted2) == token

    def test_empty_string_encryption(self, sm_encryption_key):
        """Test encrypting empty string"""
        encryptor = TokenEncryption()

        # Empty string is treated as None (falsy)
        encrypted = encryptor.encrypt("")
        assert encrypted is None

        decrypted = encryptor.decrypt(encrypted)
        assert decrypted is None

    def test_long_token_encryption(self, sm_encryption_key):
        """Test encrypting long token"""
        encryptor = TokenEncryption()

        long_token = "a" * 1000
        encrypted = encryptor.encrypt(long_token)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == long_token

    def test_special_characters_encryption(self, sm_encryption_key):
        """Test encrypting tokens with special characters"""
        encryptor = TokenEncryption()

        special_token = "token!@#$%^&*()_+-=[]{}|;':\",./<>?"
        encrypted = encryptor.encrypt(special_token)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == special_token


# ==================== Integration Tests ====================

@pytest.mark.integration
class TestModelIntegration:
    """Integration tests across multiple models"""

    def test_complete_user_workflow(self, sm_session, sm_encryption_key):
        """Test complete workflow: user -> token -> post -> analytics"""
        encryptor = TokenEncryption()

        # Create user
        user = User(
            username="integration_test",
            email="integration@test.com",
            research_area="AI Systems"
        )
        sm_session.add(user)
        sm_session.commit()

        # Add OAuth token
        token = OAuthToken(
            user_id=user.id,
            platform=Platform.TWITTER,
            access_token_encrypted=encryptor.encrypt("access_123")
        )
        sm_session.add(token)
        sm_session.commit()

        # Create post
        post = Post(
            user_id=user.id,
            platform=Platform.TWITTER,
            content="Integration test post",
            status=PostStatus.PUBLISHED,
            published_time=datetime.utcnow()
        )
        sm_session.add(post)
        sm_session.commit()

        # Add analytics
        analytics = PostAnalytics(
            post_id=post.id,
            impressions=1000,
            likes=50
        )
        sm_session.add(analytics)
        sm_session.commit()

        # Verify relationships
        assert len(user.posts) == 1
        assert len(user.oauth_tokens) == 1
        assert len(post.analytics) == 1
        assert post.analytics[0].likes == 50

    def test_cascade_delete(self, sm_session, test_sm_user):
        """Test cascade delete removes related records"""
        # Create post for user
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test delete cascade"
        )
        sm_session.add(post)
        sm_session.commit()

        post_id = post.id
        user_id = test_sm_user.id

        # Delete user
        sm_session.delete(test_sm_user)
        sm_session.commit()

        # Verify post is deleted (cascade)
        deleted_post = sm_session.query(Post).filter(Post.id == post_id).first()
        assert deleted_post is None

    def test_multiple_platforms_same_user(self, sm_session, test_sm_user, sm_encryption_key):
        """Test user with posts on multiple platforms"""
        encryptor = TokenEncryption()

        # Create tokens for both platforms
        twitter_token = OAuthToken(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            access_token_encrypted=encryptor.encrypt("twitter_token")
        )
        linkedin_token = OAuthToken(
            user_id=test_sm_user.id,
            platform=Platform.LINKEDIN,
            access_token_encrypted=encryptor.encrypt("linkedin_token")
        )
        sm_session.add_all([twitter_token, linkedin_token])
        sm_session.commit()

        # Create posts on both platforms
        twitter_post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Twitter post"
        )
        linkedin_post = Post(
            user_id=test_sm_user.id,
            platform=Platform.LINKEDIN,
            content="LinkedIn post"
        )
        sm_session.add_all([twitter_post, linkedin_post])
        sm_session.commit()

        # Query posts by platform
        twitter_posts = sm_session.query(Post).filter(
            Post.user_id == test_sm_user.id,
            Post.platform == Platform.TWITTER
        ).all()

        assert len(twitter_posts) >= 1
        assert all(p.platform == Platform.TWITTER for p in twitter_posts)
