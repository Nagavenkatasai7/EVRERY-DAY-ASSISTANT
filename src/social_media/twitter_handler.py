"""
X (Twitter) API Handler
Compliant automation using official Twitter API v2 with OAuth 1.0a
"""

import os
import time
import random
import functools
from typing import Dict, List, Optional
from datetime import datetime
import tweepy
from tweepy.errors import TweepyException, TooManyRequests, Unauthorized

from utils.logger import get_logger
from utils.exceptions import AuthenticationError, RateLimitError

logger = get_logger(__name__)


class TwitterHandler:
    """
    Handles Twitter API interactions with proper error handling and rate limiting

    Compliance Notes:
    - Uses official Twitter API v2
    - Implements OAuth 1.0a for user context
    - Respects rate limits automatically
    - Includes retry logic with exponential backoff
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_secret: str,
        dry_run: bool = False,
        is_premium: bool = None
    ):
        """Initialize Twitter API client

        Args:
            api_key: Twitter API key (consumer key)
            api_secret: Twitter API secret (consumer secret)
            access_token: User access token
            access_secret: User access token secret
            dry_run: If True, log actions without posting
            is_premium: If True, allows 25,000 character posts. If None, reads from TWITTER_PREMIUM env var.
        """
        self.dry_run = dry_run

        # Determine character limit based on premium status
        if is_premium is None:
            # Read from environment variable
            is_premium = os.getenv('TWITTER_PREMIUM', 'false').lower() == 'true'

        self.is_premium = is_premium
        self.max_chars = 25000 if is_premium else 280

        logger.info(f"Twitter account type: {'Premium (25,000 chars)' if is_premium else 'Free (280 chars)'}")

        try:
            # Initialize v2 client for posting
            self.client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_secret,
                wait_on_rate_limit=True  # Automatically handle rate limits
            )

            # Initialize v1.1 API for media uploads
            auth = tweepy.OAuth1UserHandler(
                api_key, api_secret,
                access_token, access_secret
            )
            self.api_v1 = tweepy.API(auth)

            logger.info("Twitter API client initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {str(e)}")
            raise AuthenticationError(f"Twitter authentication failed: {str(e)}")

    @staticmethod
    def exponential_backoff_retry(max_retries=5, base_delay=1.0, max_delay=60.0):
        """Decorator for exponential backoff retry logic with jitter"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except TooManyRequests as e:
                        if attempt == max_retries:
                            raise RateLimitError(f"Rate limit exceeded after {max_retries} attempts")

                        # Get reset time from headers if available
                        if hasattr(e, 'response') and e.response:
                            reset_time = int(e.response.headers.get('x-rate-limit-reset', 0))
                            wait_seconds = reset_time - int(datetime.utcnow().timestamp())
                            if wait_seconds > 0:
                                logger.warning(f"Rate limited. Waiting {wait_seconds}s until reset")
                                time.sleep(wait_seconds + 5)
                                continue

                        # Standard exponential backoff
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        jitter = delay * (0.5 + random.random())
                        logger.warning(f"Rate limit hit (attempt {attempt + 1}). Waiting {jitter:.1f}s")
                        time.sleep(jitter)

                    except Unauthorized as e:
                        logger.error(f"Authentication error: {str(e)}")
                        raise AuthenticationError(f"Twitter authentication failed: {str(e)}")

                    except TweepyException as e:
                        if attempt == max_retries:
                            raise

                        delay = min(base_delay * (2 ** attempt), max_delay)
                        jitter = delay * (0.5 + random.random())
                        logger.warning(f"API error (attempt {attempt + 1}): {str(e)}. Waiting {jitter:.1f}s")
                        time.sleep(jitter)

                raise Exception(f"Max retries ({max_retries}) exceeded")
            return wrapper
        return decorator

    @exponential_backoff_retry(max_retries=3)
    def create_tweet(self, content: str, media_paths: List[str] = None) -> Dict:
        """Create a tweet with optional media

        Args:
            content: Tweet text (max 280 characters for free tier, 25,000 for Premium)
            media_paths: Optional list of media file paths to attach

        Returns:
            Dict with tweet data: {
                'success': bool,
                'tweet_id': str,
                'text': str,
                'url': str,
                'created_at': datetime
            }
        """
        if self.dry_run:
            logger.info(f"DRY RUN: Would post tweet: {content[:50]}...")
            return {
                'success': True,
                'tweet_id': 'dry_run_12345',
                'text': content,
                'url': 'https://twitter.com/user/status/dry_run_12345',
                'created_at': datetime.utcnow(),
                'dry_run': True
            }

        # Validate content length
        if len(content) > self.max_chars:
            logger.error(f"Validation error: Tweet too long: {len(content)} chars (max {self.max_chars})")
            return {
                'success': False,
                'error': f"Tweet too long: {len(content)} chars (max {self.max_chars})",
                'error_type': 'validation'
            }

        # Upload media if provided
        media_ids = []
        if media_paths:
            for media_path in media_paths:
                try:
                    media = self.api_v1.media_upload(media_path)
                    media_ids.append(media.media_id)
                    logger.info(f"Uploaded media: {media_path}")
                except Exception as e:
                    logger.error(f"Failed to upload media {media_path}: {str(e)}")

        # Create tweet - let decorator handle retries and exceptions
        if media_ids:
            response = self.client.create_tweet(
                text=content,
                media_ids=media_ids
            )
        else:
            response = self.client.create_tweet(text=content)

        tweet_id = response.data['id']
        tweet_url = f"https://twitter.com/user/status/{tweet_id}"

        logger.info(f"✅ Tweet posted successfully: {tweet_url}")

        return {
            'success': True,
            'tweet_id': tweet_id,
            'text': content,
            'url': tweet_url,
            'created_at': datetime.utcnow()
        }

    @exponential_backoff_retry(max_retries=3)
    def get_tweet_metrics(self, tweet_id: str) -> Dict:
        """Get engagement metrics for a tweet

        Args:
            tweet_id: Twitter tweet ID

        Returns:
            Dict with metrics: {
                'impressions': int,
                'likes': int,
                'retweets': int,
                'replies': int,
                'url_clicks': int
            }
        """
        try:
            # Get tweet data with metrics
            tweet = self.client.get_tweet(
                tweet_id,
                tweet_fields=['public_metrics', 'created_at'],
                user_auth=True
            )

            if tweet.data:
                metrics = tweet.data.public_metrics
                return {
                    'tweet_id': tweet_id,
                    'likes': metrics.get('like_count', 0),
                    'retweets': metrics.get('retweet_count', 0),
                    'replies': metrics.get('reply_count', 0),
                    'quotes': metrics.get('quote_count', 0),
                    'impressions': metrics.get('impression_count', 0),
                    'created_at': tweet.data.created_at
                }
            else:
                logger.warning(f"No data found for tweet {tweet_id}")
                return {}

        except Exception as e:
            logger.error(f"Failed to get tweet metrics: {str(e)}")
            return {}

    @exponential_backoff_retry(max_retries=3)
    def get_user_metrics(self) -> Dict:
        """Get authenticated user's profile metrics

        Returns:
            Dict with user metrics: {
                'followers': int,
                'following': int,
                'tweet_count': int,
                'listed_count': int
            }
        """
        try:
            user = self.client.get_me(
                user_fields=['public_metrics']
            )

            if user.data:
                metrics = user.data.public_metrics
                return {
                    'username': user.data.username,
                    'name': user.data.name,
                    'followers': metrics.get('followers_count', 0),
                    'following': metrics.get('following_count', 0),
                    'tweet_count': metrics.get('tweet_count', 0),
                    'listed_count': metrics.get('listed_count', 0)
                }
            else:
                logger.warning("Could not fetch user metrics")
                return {}

        except Exception as e:
            logger.error(f"Failed to get user metrics: {str(e)}")
            return {}

    @exponential_backoff_retry(max_retries=3)
    def delete_tweet(self, tweet_id: str) -> bool:
        """Delete a tweet

        Args:
            tweet_id: Tweet ID to delete

        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"DRY RUN: Would delete tweet {tweet_id}")
            return True

        try:
            self.client.delete_tweet(tweet_id)
            logger.info(f"✅ Deleted tweet {tweet_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete tweet {tweet_id}: {str(e)}")
            return False

    @exponential_backoff_retry(max_retries=3)
    def search_recent_tweets(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search recent tweets (past 7 days)

        Args:
            query: Search query
            max_results: Number of tweets to return (max 100)

        Returns:
            List of tweet data dictionaries
        """
        try:
            tweets = self.client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),
                tweet_fields=['created_at', 'public_metrics', 'author_id']
            )

            results = []
            if tweets.data:
                for tweet in tweets.data:
                    results.append({
                        'id': tweet.id,
                        'text': tweet.text,
                        'created_at': tweet.created_at,
                        'metrics': tweet.public_metrics
                    })

            return results

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []

    def verify_credentials(self) -> bool:
        """Verify API credentials are valid

        Returns:
            True if credentials valid, False otherwise
        """
        try:
            self.client.get_me()
            logger.info("✅ Twitter credentials verified")
            return True
        except Exception as e:
            logger.error(f"❌ Credential verification failed: {str(e)}")
            return False

    def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status

        Returns:
            Dict with rate limit info for key endpoints
        """
        try:
            # Note: This requires additional API call which counts against limits
            # Use sparingly
            limits = self.client.get_rate_limit_status()
            return limits
        except Exception as e:
            logger.error(f"Failed to get rate limits: {str(e)}")
            return {}


# Rate limit constants for different tiers
TWITTER_RATE_LIMITS = {
    'free': {
        'tweets_per_24h': 17,
        'tweets_per_month': 500,
        'read_requests_per_month': 10000
    },
    'basic': {
        'tweets_per_24h': 100,
        'tweets_per_month': 3000,
        'read_requests_per_month': 100000
    },
    'pro': {
        'tweets_per_24h': 300,
        'tweets_per_month': 10000,
        'read_requests_per_month': 1000000
    }
}


class RateLimitTracker:
    """Tracks API usage to stay within rate limits"""

    def __init__(self, tier: str = 'basic'):
        """Initialize rate limit tracker

        Args:
            tier: Twitter API tier ('free', 'basic', 'pro')
        """
        self.tier = tier
        self.limits = TWITTER_RATE_LIMITS.get(tier, TWITTER_RATE_LIMITS['basic'])
        self.tweets_today = 0
        self.tweets_month = 0
        self.last_reset = datetime.utcnow()

    def can_post(self) -> bool:
        """Check if posting is allowed within rate limits"""
        if self.tweets_today >= self.limits['tweets_per_24h']:
            logger.warning(f"Daily tweet limit reached: {self.tweets_today}/{self.limits['tweets_per_24h']}")
            return False
        if self.tweets_month >= self.limits['tweets_per_month']:
            logger.warning(f"Monthly tweet limit reached: {self.tweets_month}/{self.limits['tweets_per_month']}")
            return False
        return True

    def record_post(self):
        """Record a posted tweet"""
        self.tweets_today += 1
        self.tweets_month += 1

    def reset_daily(self):
        """Reset daily counter"""
        self.tweets_today = 0
        self.last_reset = datetime.utcnow()

    def get_status(self) -> Dict:
        """Get current usage status"""
        return {
            'tier': self.tier,
            'tweets_today': self.tweets_today,
            'tweets_month': self.tweets_month,
            'daily_limit': self.limits['tweets_per_24h'],
            'monthly_limit': self.limits['tweets_per_month'],
            'daily_remaining': self.limits['tweets_per_24h'] - self.tweets_today,
            'monthly_remaining': self.limits['tweets_per_month'] - self.tweets_month
        }
