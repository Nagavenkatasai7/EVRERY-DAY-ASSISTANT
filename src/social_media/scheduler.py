"""
Post Scheduler using APScheduler
Schedules and executes social media posts with retry logic
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED

from utils.logger import get_logger
from .models import Post, PostStatus, Platform, DatabaseManager
from . import models
from .twitter_handler import TwitterHandler

logger = get_logger(__name__)


class PostScheduler:
    """
    Schedules and executes social media posts

    Features:
    - Persistent job store (survives restarts)
    - Automatic retry on failure (max 3 attempts)
    - Timezone support
    - Job monitoring and error handling
    - Pause/resume/cancel capabilities
    """

    def __init__(self, db_manager: DatabaseManager = None, timezone: str = 'UTC', use_memory_store: bool = False):
        """Initialize post scheduler

        Args:
            db_manager: Database manager instance
            timezone: Timezone for scheduling (default: UTC)
            use_memory_store: Use memory job store instead of SQLAlchemy (for testing)
        """
        self.db_manager = db_manager or DatabaseManager()
        self.timezone = timezone

        # Initialize scheduler (use memory store for testing to avoid pickling issues)
        if use_memory_store:
            # Use default memory store (no jobstores param needed)
            self.scheduler = AsyncIOScheduler(timezone=timezone)
        else:
            # Setup persistent job store for production
            jobstores = {
                'default': SQLAlchemyJobStore(
                    url='sqlite:///social_media_jobs.db',
                    tablename='scheduled_jobs'
                )
            }
            self.scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                timezone=timezone
            )

        # Add event listeners
        self.scheduler.add_listener(
            self._job_executed_callback,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED
        )

        # Track running state
        self._running = False

        logger.info(f"Post scheduler initialized (timezone: {timezone})")

    def start(self):
        """Start the scheduler"""
        if not self._running:
            try:
                # Try to get the running event loop
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, create and set a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Set the event loop for the scheduler
            self.scheduler._eventloop = loop
            self.scheduler.start()
            self._running = True
            logger.info("✅ Post scheduler started")

    def shutdown(self, wait: bool = True):
        """Shutdown the scheduler

        Args:
            wait: Wait for running jobs to complete
        """
        if self._running:
            self.scheduler.shutdown(wait=wait)
            self._running = False
            logger.info("🛑 Post scheduler shutdown")

    def schedule_post(
        self,
        post_id: int,
        scheduled_time: datetime,
        user_id: int
    ) -> str:
        """Schedule a post for future publishing

        Args:
            post_id: Post ID to schedule
            scheduled_time: When to publish
            user_id: User ID who owns the post

        Returns:
            Job ID string
        """
        try:
            # Validate post exists
            session = self.db_manager.get_session()
            post = session.query(Post).filter(Post.id == post_id).first()

            if not post:
                raise ValueError(f"Post {post_id} not found")

            if post.status not in [PostStatus.DRAFT, PostStatus.SCHEDULED]:
                raise ValueError(f"Post {post_id} has invalid status: {post.status}")

            # Update post status
            post.status = PostStatus.SCHEDULED
            post.scheduled_time = scheduled_time
            session.commit()
            session.close()

            # Schedule job
            job = self.scheduler.add_job(
                self._execute_post,
                trigger=DateTrigger(run_date=scheduled_time),
                args=[post_id, user_id],
                id=f"post_{post_id}",
                replace_existing=True,
                misfire_grace_time=300  # 5 minutes grace period
            )

            logger.info(f"📅 Scheduled post {post_id} for {scheduled_time}")
            return job.id

        except Exception as e:
            logger.error(f"Failed to schedule post {post_id}: {str(e)}")
            raise

    def cancel_scheduled_post(self, post_id: int) -> bool:
        """Cancel a scheduled post

        Args:
            post_id: Post ID to cancel

        Returns:
            True if cancelled successfully
        """
        try:
            job_id = f"post_{post_id}"

            # Remove job from scheduler
            self.scheduler.remove_job(job_id)

            # Update post status
            session = self.db_manager.get_session()
            post = session.query(Post).filter(Post.id == post_id).first()

            if post:
                post.status = PostStatus.CANCELLED
                session.commit()

            session.close()

            logger.info(f"❌ Cancelled scheduled post {post_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel post {post_id}: {str(e)}")
            return False

    def reschedule_post(
        self,
        post_id: int,
        new_time: datetime
    ) -> bool:
        """Reschedule a post to a different time

        Args:
            post_id: Post ID to reschedule
            new_time: New scheduled time

        Returns:
            True if rescheduled successfully
        """
        try:
            job_id = f"post_{post_id}"

            # Reschedule job
            self.scheduler.reschedule_job(
                job_id,
                trigger=DateTrigger(run_date=new_time)
            )

            # Update post
            session = self.db_manager.get_session()
            post = session.query(Post).filter(Post.id == post_id).first()

            if post:
                post.scheduled_time = new_time
                session.commit()

            session.close()

            logger.info(f"🔄 Rescheduled post {post_id} to {new_time}")
            return True

        except Exception as e:
            logger.error(f"Failed to reschedule post {post_id}: {str(e)}")
            return False

    def get_scheduled_posts(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[Dict]:
        """Get list of scheduled posts for a user

        Args:
            user_id: User ID
            limit: Maximum number of posts to return

        Returns:
            List of scheduled post dictionaries
        """
        try:
            session = self.db_manager.get_session()

            posts = session.query(Post).filter(
                Post.user_id == user_id,
                Post.status == PostStatus.SCHEDULED
            ).order_by(Post.scheduled_time).limit(limit).all()

            scheduled = []
            for post in posts:
                # Get job info from scheduler
                job_id = f"post_{post.id}"
                job = self.scheduler.get_job(job_id)

                scheduled.append({
                    'post_id': post.id,
                    'content': post.content,
                    'platform': post.platform.value,
                    'content_type': post.content_type.value if post.content_type else None,
                    'scheduled_time': post.scheduled_time,
                    'job_id': job_id,
                    'job_exists': job is not None,
                    'next_run_time': job.next_run_time if job else None
                })

            session.close()
            return scheduled

        except Exception as e:
            logger.error(f"Failed to get scheduled posts: {str(e)}")
            return []

    async def _execute_post(self, post_id: int, user_id: int):
        """Execute a scheduled post

        Args:
            post_id: Post ID to publish
            user_id: User ID who owns the post
        """
        session = None
        try:
            logger.info(f"🚀 Executing post {post_id}")

            session = self.db_manager.get_session()

            # Get post
            post = session.query(Post).filter(Post.id == post_id).first()
            if not post:
                raise ValueError(f"Post {post_id} not found")

            # Get user's OAuth token
            from .models import OAuthToken
            token_record = session.query(OAuthToken).filter(
                OAuthToken.user_id == user_id,
                OAuthToken.platform == post.platform
            ).first()

            if not token_record:
                raise ValueError(f"No OAuth token found for user {user_id} on {post.platform}")

            # Decrypt tokens
            access_token = models.token_encryptor.decrypt(token_record.access_token_encrypted)
            access_secret = models.token_encryptor.decrypt(token_record.token_secret_encrypted)

            # Publish based on platform
            if post.platform == Platform.TWITTER:
                result = await self._publish_to_twitter(
                    post, access_token, access_secret
                )
            elif post.platform == Platform.LINKEDIN:
                # LinkedIn automation not supported (compliance)
                raise ValueError("LinkedIn automated posting is not supported (ToS violation)")
            else:
                raise ValueError(f"Unsupported platform: {post.platform}")

            # Update post status
            if result['success']:
                post.status = PostStatus.PUBLISHED
                post.published_time = datetime.utcnow()
                post.external_post_id = result.get('tweet_id')
                post.external_url = result.get('url')
                post.error_message = None

                logger.info(f"✅ Successfully published post {post_id}")
            else:
                raise Exception(result.get('error', 'Unknown error'))

            session.commit()

        except ValueError as e:
            # ValueError indicates a configuration error - re-raise immediately
            logger.error(f"❌ Configuration error for post {post_id}: {str(e)}")
            if session:
                session.close()
            raise
        except Exception as e:
            error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
            logger.error(f"❌ Failed to execute post {post_id}: {error_msg}")

            if session and post:
                # Check if we can retry before incrementing
                if post.retry_count < post.max_retries:
                    post.retry_count += 1
                    post.error_message = str(e)
                    post.status = PostStatus.SCHEDULED

                    # Reschedule for 5 minutes later
                    retry_time = datetime.utcnow() + timedelta(minutes=5)
                    post.scheduled_time = retry_time

                    logger.warning(f"🔄 Retry {post.retry_count}/{post.max_retries} scheduled for {retry_time}")

                    # Reschedule job
                    self.scheduler.add_job(
                        self._execute_post,
                        trigger=DateTrigger(run_date=retry_time),
                        args=[post_id, user_id],
                        id=f"post_{post_id}",
                        replace_existing=True
                    )
                else:
                    # Max retries reached - don't increment further
                    post.status = PostStatus.FAILED
                    post.error_message = str(e)
                    logger.error(f"❌ Post {post_id} failed after {post.max_retries} retries")

                session.commit()

        finally:
            if session:
                session.close()

    async def _publish_to_twitter(
        self,
        post: Post,
        access_token: str,
        access_secret: str
    ) -> Dict:
        """Publish post to Twitter

        Args:
            post: Post object
            access_token: Decrypted access token
            access_secret: Decrypted access secret

        Returns:
            Result dictionary
        """
        try:
            # Get Twitter API credentials from environment
            import os
            api_key = os.getenv('TWITTER_API_KEY')
            api_secret = os.getenv('TWITTER_API_SECRET')

            if not api_key or not api_secret:
                raise ValueError("Twitter API credentials not configured")

            # Initialize Twitter handler
            twitter = TwitterHandler(
                api_key=api_key,
                api_secret=api_secret,
                access_token=access_token,
                access_secret=access_secret,
                dry_run=False
            )

            # Create tweet
            result = twitter.create_tweet(
                content=post.content,
                media_paths=post.media_urls if post.media_urls else None
            )

            return result

        except Exception as e:
            logger.error(f"Twitter publish failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _job_executed_callback(self, event):
        """Callback for job execution events"""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.info(f"Job {event.job_id} executed successfully")

    def get_scheduler_status(self) -> Dict:
        """Get scheduler status and statistics

        Returns:
            Status dictionary
        """
        return {
            'running': self._running,
            'timezone': self.timezone,
            'num_jobs': len(self.scheduler.get_jobs()),
            'jobs': [
                {
                    'id': job.id,
                    'next_run_time': job.next_run_time,
                    'trigger': str(job.trigger)
                }
                for job in self.scheduler.get_jobs()
            ]
        }

    def pause_scheduler(self):
        """Pause all job execution"""
        self.scheduler.pause()
        logger.info("⏸️  Scheduler paused")

    def resume_scheduler(self):
        """Resume job execution"""
        self.scheduler.resume()
        logger.info("▶️  Scheduler resumed")
