"""
Comprehensive Scheduler Tests
Tests job scheduling, retry logic, and execution

Coverage targets:
- Job scheduling with APScheduler
- Post execution workflow
- Retry logic with exponential backoff
- Job cancellation and rescheduling
- Error handling and status updates
- Platform-specific publishing
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from src.social_media.scheduler import PostScheduler
from src.social_media.models import (
    Post, PostStatus, Platform, User, OAuthToken,
    DatabaseManager, TokenEncryption
)


# ==================== Initialization Tests ====================

@pytest.mark.unit
class TestPostSchedulerInit:
    """Test PostScheduler initialization"""

    def test_init_with_defaults(self, sm_db_manager):
        """Test initialization with default parameters"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        assert scheduler.db_manager is sm_db_manager
        assert scheduler.timezone == 'UTC'
        assert scheduler.scheduler is not None
        assert scheduler._running is False

    def test_init_with_custom_timezone(self, sm_db_manager):
        """Test initialization with custom timezone"""
        scheduler = PostScheduler(
            db_manager=sm_db_manager,
            timezone='America/New_York'
        )

        assert scheduler.timezone == 'America/New_York'

    def test_init_creates_job_store(self, sm_db_manager):
        """Test initialization creates persistent job store"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=False)

        jobstores = scheduler.scheduler._jobstores
        assert 'default' in jobstores


# ==================== Start/Shutdown Tests ====================

@pytest.mark.unit
class TestSchedulerLifecycle:
    """Test scheduler start/shutdown lifecycle"""

    def test_start_scheduler(self, sm_db_manager):
        """Test starting the scheduler"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        scheduler.start()

        assert scheduler._running is True
        assert scheduler.scheduler.running is True

        scheduler.shutdown()

    def test_start_already_running(self, sm_db_manager):
        """Test starting already running scheduler"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        scheduler.start()
        assert scheduler._running is True

        # Start again - should be idempotent
        scheduler.start()
        assert scheduler._running is True

        scheduler.shutdown()

    def test_shutdown_scheduler(self, sm_db_manager):
        """Test shutting down the scheduler"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        scheduler.start()
        scheduler.shutdown(wait=False)

        assert scheduler._running is False

    def test_shutdown_with_wait(self, sm_db_manager):
        """Test shutdown waits for running jobs"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        scheduler.start()
        scheduler.shutdown(wait=True)

        assert scheduler._running is False


# ==================== Schedule Post Tests ====================

@pytest.mark.unit
class TestSchedulePost:
    """Test post scheduling functionality"""

    def test_schedule_draft_post(self, sm_db_manager, sm_session, test_sm_user):
        """Test scheduling a draft post"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        # Create draft post
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Scheduled test tweet",
            status=PostStatus.DRAFT
        )
        sm_session.add(post)
        sm_session.commit()

        scheduled_time = datetime.utcnow() + timedelta(hours=2)

        # Schedule post
        job_id = scheduler.schedule_post(
            post_id=post.id,
            scheduled_time=scheduled_time,
            user_id=test_sm_user.id
        )

        assert job_id == f"post_{post.id}"

        # Verify post status updated
        sm_session.refresh(post)
        assert post.status == PostStatus.SCHEDULED
        assert post.scheduled_time == scheduled_time

        scheduler.shutdown()

    def test_schedule_post_invalid_status(self, sm_db_manager, sm_session, test_sm_user):
        """Test scheduling post with invalid status"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        # Create published post (can't be scheduled)
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Already published",
            status=PostStatus.PUBLISHED
        )
        sm_session.add(post)
        sm_session.commit()

        scheduled_time = datetime.utcnow() + timedelta(hours=2)

        # Should raise error
        with pytest.raises(ValueError):
            scheduler.schedule_post(
                post_id=post.id,
                scheduled_time=scheduled_time,
                user_id=test_sm_user.id
            )

        scheduler.shutdown()

    def test_schedule_post_not_found(self, sm_db_manager, test_sm_user):
        """Test scheduling non-existent post"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        scheduled_time = datetime.utcnow() + timedelta(hours=2)

        with pytest.raises(ValueError):
            scheduler.schedule_post(
                post_id=99999,
                scheduled_time=scheduled_time,
                user_id=test_sm_user.id
            )

        scheduler.shutdown()

    def test_schedule_post_replaces_existing(self, sm_db_manager, sm_session, test_sm_user):
        """Test scheduling replaces existing job"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.DRAFT
        )
        sm_session.add(post)
        sm_session.commit()

        time1 = datetime.utcnow() + timedelta(hours=1)
        time2 = datetime.utcnow() + timedelta(hours=2)

        # Schedule first time
        job_id1 = scheduler.schedule_post(post.id, time1, test_sm_user.id)

        # Schedule again with different time (should replace)
        job_id2 = scheduler.schedule_post(post.id, time2, test_sm_user.id)

        assert job_id1 == job_id2

        scheduler.shutdown()


# ==================== Cancel Post Tests ====================

@pytest.mark.unit
class TestCancelScheduledPost:
    """Test canceling scheduled posts"""

    def test_cancel_scheduled_post(self, sm_db_manager, sm_session, test_sm_user):
        """Test canceling a scheduled post"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.DRAFT
        )
        sm_session.add(post)
        sm_session.commit()

        scheduled_time = datetime.utcnow() + timedelta(hours=2)
        scheduler.schedule_post(post.id, scheduled_time, test_sm_user.id)

        # Cancel post
        result = scheduler.cancel_scheduled_post(post.id)

        assert result is True

        # Verify status updated
        sm_session.refresh(post)
        assert post.status == PostStatus.CANCELLED

        scheduler.shutdown()

    def test_cancel_non_existent_job(self, sm_db_manager):
        """Test canceling non-existent job"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        result = scheduler.cancel_scheduled_post(99999)

        assert result is False

        scheduler.shutdown()


# ==================== Reschedule Post Tests ====================

@pytest.mark.unit
class TestReschedulePost:
    """Test rescheduling posts"""

    def test_reschedule_post(self, sm_db_manager, sm_session, test_sm_user):
        """Test rescheduling a post to new time"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.DRAFT
        )
        sm_session.add(post)
        sm_session.commit()

        original_time = datetime.utcnow() + timedelta(hours=2)
        new_time = datetime.utcnow() + timedelta(hours=4)

        # Schedule
        scheduler.schedule_post(post.id, original_time, test_sm_user.id)

        # Reschedule
        result = scheduler.reschedule_post(post.id, new_time)

        assert result is True

        # Verify time updated
        sm_session.refresh(post)
        assert post.scheduled_time == new_time

        scheduler.shutdown()

    def test_reschedule_non_existent_job(self, sm_db_manager):
        """Test rescheduling non-existent job"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        new_time = datetime.utcnow() + timedelta(hours=4)
        result = scheduler.reschedule_post(99999, new_time)

        assert result is False

        scheduler.shutdown()


# ==================== Get Scheduled Posts Tests ====================

@pytest.mark.unit
class TestGetScheduledPosts:
    """Test retrieving scheduled posts"""

    def test_get_scheduled_posts(self, sm_db_manager, sm_session, test_sm_user):
        """Test getting list of scheduled posts"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        # Create and schedule multiple posts
        post1 = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Post 1",
            status=PostStatus.DRAFT
        )
        post2 = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Post 2",
            status=PostStatus.DRAFT
        )
        sm_session.add_all([post1, post2])
        sm_session.commit()

        time1 = datetime.utcnow() + timedelta(hours=1)
        time2 = datetime.utcnow() + timedelta(hours=2)

        scheduler.schedule_post(post1.id, time1, test_sm_user.id)
        scheduler.schedule_post(post2.id, time2, test_sm_user.id)

        # Get scheduled posts
        scheduled = scheduler.get_scheduled_posts(test_sm_user.id)

        assert len(scheduled) >= 2
        assert all('post_id' in p for p in scheduled)
        assert all('scheduled_time' in p for p in scheduled)

        scheduler.shutdown()

    def test_get_scheduled_posts_sorted(self, sm_db_manager, sm_session, test_sm_user):
        """Test scheduled posts are sorted by time"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        posts = []
        times = []
        for i in range(3):
            post = Post(
                user_id=test_sm_user.id,
                platform=Platform.TWITTER,
                content=f"Post {i}",
                status=PostStatus.DRAFT
            )
            posts.append(post)
            times.append(datetime.utcnow() + timedelta(hours=i+1))

        sm_session.add_all(posts)
        sm_session.commit()

        for post, time in zip(posts, times):
            scheduler.schedule_post(post.id, time, test_sm_user.id)

        scheduled = scheduler.get_scheduled_posts(test_sm_user.id)

        # Verify sorted by time
        if len(scheduled) > 1:
            for i in range(len(scheduled) - 1):
                assert scheduled[i]['scheduled_time'] <= scheduled[i+1]['scheduled_time']

        scheduler.shutdown()

    def test_get_scheduled_posts_with_limit(self, sm_db_manager, sm_session, test_sm_user):
        """Test limit parameter"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        # Create many posts
        posts = []
        for i in range(10):
            post = Post(
                user_id=test_sm_user.id,
                platform=Platform.TWITTER,
                content=f"Post {i}",
                status=PostStatus.DRAFT
            )
            posts.append(post)

        sm_session.add_all(posts)
        sm_session.commit()

        for post in posts:
            time = datetime.utcnow() + timedelta(hours=1)
            scheduler.schedule_post(post.id, time, test_sm_user.id)

        # Get with limit
        scheduled = scheduler.get_scheduled_posts(test_sm_user.id, limit=5)

        assert len(scheduled) <= 5

        scheduler.shutdown()


# ==================== Post Execution Tests ====================

@pytest.mark.asyncio
@pytest.mark.unit
class TestExecutePost:
    """Test post execution"""

    async def test_execute_post_twitter_success(self, sm_db_manager, sm_session,
                                                 test_sm_user, test_twitter_token, mock_tweepy):
        """Test successful Twitter post execution"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.SCHEDULED
        )
        sm_session.add(post)
        sm_session.commit()

        with patch.dict('os.environ', {
            'TWITTER_API_KEY': 'test_key',
            'TWITTER_API_SECRET': 'test_secret'
        }):
            await scheduler._execute_post(post.id, test_sm_user.id)

        # Verify post published
        sm_session.refresh(post)
        assert post.status == PostStatus.PUBLISHED
        assert post.published_time is not None
        assert post.external_post_id is not None

    async def test_execute_post_not_found(self, sm_db_manager, test_sm_user):
        """Test executing non-existent post"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        with pytest.raises(ValueError):
            await scheduler._execute_post(99999, test_sm_user.id)

    async def test_execute_post_no_oauth_token(self, sm_db_manager, sm_session, test_sm_user):
        """Test executing post without OAuth token"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.SCHEDULED
        )
        sm_session.add(post)
        sm_session.commit()

        # Remove OAuth token
        sm_session.query(OAuthToken).filter(
            OAuthToken.user_id == test_sm_user.id
        ).delete()
        sm_session.commit()

        with pytest.raises(ValueError):
            await scheduler._execute_post(post.id, test_sm_user.id)

    async def test_execute_post_linkedin_not_supported(self, sm_db_manager, sm_session,
                                                       test_sm_user, sm_encryption_key):
        """Test LinkedIn posting raises error (not supported)"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        encryptor = TokenEncryption()

        # Create LinkedIn token
        linkedin_token = OAuthToken(
            user_id=test_sm_user.id,
            platform=Platform.LINKEDIN,
            access_token_encrypted=encryptor.encrypt("linkedin_token")
        )
        sm_session.add(linkedin_token)

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.LINKEDIN,
            content="Test LinkedIn post",
            status=PostStatus.SCHEDULED
        )
        sm_session.add(post)
        sm_session.commit()

        with pytest.raises(ValueError, match="LinkedIn automated posting is not supported"):
            await scheduler._execute_post(post.id, test_sm_user.id)


# ==================== Retry Logic Tests ====================

@pytest.mark.asyncio
@pytest.mark.unit
class TestRetryLogic:
    """Test retry logic for failed posts"""

    async def test_retry_on_failure(self, sm_db_manager, sm_session, test_sm_user,
                                   test_twitter_token, mock_tweepy):
        """Test post is retried on failure"""
        mock_tweepy.return_value.create_tweet.side_effect = Exception("API Error")

        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.SCHEDULED,
            max_retries=3
        )
        sm_session.add(post)
        sm_session.commit()

        with patch.dict('os.environ', {
            'TWITTER_API_KEY': 'test_key',
            'TWITTER_API_SECRET': 'test_secret'
        }):
            await scheduler._execute_post(post.id, test_sm_user.id)

        # Verify retry scheduled
        sm_session.refresh(post)
        assert post.retry_count == 1
        assert post.status == PostStatus.SCHEDULED
        assert post.error_message is not None

        scheduler.shutdown()

    async def test_max_retries_reached(self, sm_db_manager, sm_session, test_sm_user,
                                      test_twitter_token, mock_tweepy):
        """Test post marked as failed after max retries"""
        mock_tweepy.return_value.create_tweet.side_effect = Exception("API Error")

        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.SCHEDULED,
            retry_count=3,
            max_retries=3
        )
        sm_session.add(post)
        sm_session.commit()

        with patch.dict('os.environ', {
            'TWITTER_API_KEY': 'test_key',
            'TWITTER_API_SECRET': 'test_secret'
        }):
            await scheduler._execute_post(post.id, test_sm_user.id)

        # Verify marked as failed
        sm_session.refresh(post)
        assert post.status == PostStatus.FAILED
        assert post.retry_count == 3

    async def test_retry_time_calculation(self, sm_db_manager, sm_session, test_sm_user,
                                         test_twitter_token, mock_tweepy):
        """Test retry scheduled for 5 minutes later"""
        mock_tweepy.return_value.create_tweet.side_effect = Exception("API Error")

        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet",
            status=PostStatus.SCHEDULED
        )
        sm_session.add(post)
        sm_session.commit()

        original_time = datetime.utcnow()

        with patch.dict('os.environ', {
            'TWITTER_API_KEY': 'test_key',
            'TWITTER_API_SECRET': 'test_secret'
        }):
            await scheduler._execute_post(post.id, test_sm_user.id)

        sm_session.refresh(post)

        # Verify scheduled for ~5 minutes later
        time_diff = (post.scheduled_time - original_time).total_seconds()
        assert 250 <= time_diff <= 350  # ~5 minutes with some tolerance

        scheduler.shutdown()


# ==================== Twitter Publishing Tests ====================

@pytest.mark.asyncio
@pytest.mark.unit
class TestPublishToTwitter:
    """Test Twitter publishing logic"""

    async def test_publish_to_twitter_success(self, sm_db_manager, sm_session,
                                             test_sm_user, mock_tweepy):
        """Test successful Twitter publishing"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet"
        )

        with patch.dict('os.environ', {
            'TWITTER_API_KEY': 'test_key',
            'TWITTER_API_SECRET': 'test_secret'
        }):
            result = await scheduler._publish_to_twitter(
                post, "access_token", "access_secret"
            )

        assert result['success'] is True
        assert 'tweet_id' in result

    async def test_publish_to_twitter_no_credentials(self, sm_db_manager, sm_session, test_sm_user):
        """Test publishing without credentials"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Test tweet"
        )

        with patch.dict('os.environ', {}, clear=True):
            result = await scheduler._publish_to_twitter(
                post, "access_token", "access_secret"
            )

        assert result['success'] is False
        assert 'error' in result

    async def test_publish_with_media(self, sm_db_manager, sm_session,
                                     test_sm_user, mock_tweepy):
        """Test publishing with media URLs"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Tweet with media",
            media_urls=["/path/to/image.jpg"]
        )

        with patch.dict('os.environ', {
            'TWITTER_API_KEY': 'test_key',
            'TWITTER_API_SECRET': 'test_secret'
        }):
            result = await scheduler._publish_to_twitter(
                post, "access_token", "access_secret"
            )

        assert result['success'] is True


# ==================== Scheduler Status Tests ====================

@pytest.mark.unit
class TestSchedulerStatus:
    """Test scheduler status and monitoring"""

    def test_get_scheduler_status(self, sm_db_manager):
        """Test getting scheduler status"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        status = scheduler.get_scheduler_status()

        assert 'running' in status
        assert 'timezone' in status
        assert 'num_jobs' in status
        assert 'jobs' in status
        assert status['running'] is True

        scheduler.shutdown()

    def test_pause_scheduler(self, sm_db_manager):
        """Test pausing scheduler"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        scheduler.pause_scheduler()

        assert scheduler.scheduler.state == 2  # STATE_PAUSED

        scheduler.shutdown()

    def test_resume_scheduler(self, sm_db_manager):
        """Test resuming scheduler"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        scheduler.pause_scheduler()
        scheduler.resume_scheduler()

        assert scheduler.scheduler.state == 1  # STATE_RUNNING

        scheduler.shutdown()


# ==================== Job Event Tests ====================

@pytest.mark.unit
class TestJobEvents:
    """Test job event callbacks"""

    def test_job_executed_callback_success(self, sm_db_manager):
        """Test callback on successful job execution"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        mock_event = MagicMock()
        mock_event.job_id = "test_job"
        mock_event.exception = None

        # Should not raise exception
        scheduler._job_executed_callback(mock_event)

    def test_job_executed_callback_failure(self, sm_db_manager):
        """Test callback on job execution failure"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)

        mock_event = MagicMock()
        mock_event.job_id = "test_job"
        mock_event.exception = Exception("Job failed")

        # Should not raise exception
        scheduler._job_executed_callback(mock_event)


# ==================== Integration Tests ====================

@pytest.mark.integration
class TestSchedulerIntegration:
    """Integration tests for PostScheduler"""

    def test_full_scheduling_workflow(self, sm_db_manager, sm_session, test_sm_user):
        """Test complete scheduling workflow"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        # Create post
        post = Post(
            user_id=test_sm_user.id,
            platform=Platform.TWITTER,
            content="Integration test tweet",
            status=PostStatus.DRAFT
        )
        sm_session.add(post)
        sm_session.commit()

        # Schedule
        scheduled_time = datetime.utcnow() + timedelta(hours=2)
        job_id = scheduler.schedule_post(post.id, scheduled_time, test_sm_user.id)

        # Verify scheduled
        scheduled = scheduler.get_scheduled_posts(test_sm_user.id)
        assert len(scheduled) > 0

        # Reschedule
        new_time = datetime.utcnow() + timedelta(hours=3)
        scheduler.reschedule_post(post.id, new_time)

        # Verify rescheduled
        sm_session.refresh(post)
        assert post.scheduled_time == new_time

        # Cancel
        scheduler.cancel_scheduled_post(post.id)

        # Verify cancelled
        sm_session.refresh(post)
        assert post.status == PostStatus.CANCELLED

        scheduler.shutdown()

    def test_multiple_posts_scheduling(self, sm_db_manager, sm_session, test_sm_user):
        """Test scheduling multiple posts"""
        scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
        scheduler.start()

        posts = []
        for i in range(5):
            post = Post(
                user_id=test_sm_user.id,
                platform=Platform.TWITTER,
                content=f"Test tweet {i}",
                status=PostStatus.DRAFT
            )
            posts.append(post)

        sm_session.add_all(posts)
        sm_session.commit()

        # Schedule all posts
        base_time = datetime.utcnow()
        for i, post in enumerate(posts):
            scheduled_time = base_time + timedelta(hours=i+1)
            scheduler.schedule_post(post.id, scheduled_time, test_sm_user.id)

        # Verify all scheduled
        scheduled = scheduler.get_scheduled_posts(test_sm_user.id)
        assert len(scheduled) >= 5

        scheduler.shutdown()
