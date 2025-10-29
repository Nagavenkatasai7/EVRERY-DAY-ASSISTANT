"""
Comprehensive Twitter Handler Tests
Tests Twitter API integration, rate limiting, retry logic, and error handling

Coverage targets:
- OAuth authentication
- Tweet creation with dry-run mode
- Rate limit handling
- Retry logic with exponential backoff
- Error handling and exceptions
- Media upload
- Metrics retrieval
"""

import pytest
import time
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime
from tweepy.errors import TweepyException, TooManyRequests, Unauthorized

from src.social_media.twitter_handler import (
    TwitterHandler, RateLimitTracker, TWITTER_RATE_LIMITS
)
from utils.exceptions import AuthenticationError, RateLimitError


# ==================== TwitterHandler Initialization Tests ====================

@pytest.mark.unit
class TestTwitterHandlerInit:
    """Test TwitterHandler initialization"""

    def test_init_success(self, mock_tweepy):
        """Test successful initialization"""
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        assert handler.dry_run is False
        assert handler.client is not None

    def test_init_with_dry_run(self, mock_tweepy):
        """Test initialization with dry-run mode"""
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret",
            dry_run=True
        )

        assert handler.dry_run is True

    def test_init_with_invalid_credentials(self):
        """Test initialization with invalid credentials"""
        with patch('tweepy.Client', side_effect=Exception("Invalid credentials")):
            with pytest.raises(AuthenticationError):
                TwitterHandler(
                    api_key="invalid",
                    api_secret="invalid",
                    access_token="invalid",
                    access_secret="invalid"
                )


# ==================== Tweet Creation Tests ====================

@pytest.mark.unit
class TestCreateTweet:
    """Test tweet creation functionality"""

    def test_create_tweet_success(self, mock_tweepy):
        """Test successful tweet creation"""
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        result = handler.create_tweet("This is a test tweet")

        assert result['success'] is True
        assert 'tweet_id' in result
        assert result['text'] == "This is a test tweet"
        assert 'url' in result
        assert 'created_at' in result

    def test_create_tweet_dry_run(self, mock_tweepy):
        """Test tweet creation in dry-run mode"""
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret",
            dry_run=True
        )

        result = handler.create_tweet("Test dry run tweet")

        assert result['success'] is True
        assert result['dry_run'] is True
        assert result['tweet_id'] == 'dry_run_12345'
        assert result['text'] == "Test dry run tweet"

    def test_create_tweet_too_long(self, mock_tweepy):
        """Test tweet validation for length"""
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        # Test with tweet longer than premium limit (25,000 chars)
        long_tweet = "a" * 25001  # 25,001 characters (exceeds premium limit)
        result = handler.create_tweet(long_tweet)

        assert result['success'] is False
        assert 'error' in result
        assert 'too long' in result['error'].lower()
        assert result['error_type'] == 'validation'

    def test_create_tweet_with_media(self, mock_tweepy):
        """Test tweet creation with media"""
        with patch('tweepy.API') as mock_api:
            mock_media = MagicMock()
            mock_media.media_id = "123456789"
            mock_api.return_value.media_upload.return_value = mock_media

            handler = TwitterHandler(
                api_key="test_key",
                api_secret="test_secret",
                access_token="test_token",
                access_secret="test_token_secret"
            )

            result = handler.create_tweet(
                "Tweet with image",
                media_paths=["/path/to/image.jpg"]
            )

            assert result['success'] is True

    def test_create_tweet_media_upload_failure(self, mock_tweepy):
        """Test handling media upload failure"""
        with patch('tweepy.API') as mock_api:
            mock_api.return_value.media_upload.side_effect = Exception("Upload failed")

            handler = TwitterHandler(
                api_key="test_key",
                api_secret="test_secret",
                access_token="test_token",
                access_secret="test_token_secret"
            )

            # Should still succeed but without media
            result = handler.create_tweet(
                "Tweet with failed media",
                media_paths=["/path/to/image.jpg"]
            )

            # Tweet created but media failed
            assert result['success'] is True

    def test_create_tweet_api_error(self, mock_tweepy):
        """Test handling general API errors"""
        mock_tweepy.return_value.create_tweet.side_effect = TweepyException("API Error")

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        # API errors should be retried and eventually raise an exception
        with patch('time.sleep'):  # Speed up test by mocking sleep
            with pytest.raises(Exception):
                handler.create_tweet("Test error handling")


# ==================== Rate Limiting Tests ====================

@pytest.mark.unit
class TestRateLimiting:
    """Test rate limit handling"""

    def test_rate_limit_with_retry(self, mock_tweepy):
        """Test automatic retry on rate limit"""
        # First call raises rate limit, second succeeds
        mock_response = MagicMock()
        mock_response.data = {'id': '1234567890', 'text': 'Test'}

        # Create mock response for TooManyRequests
        mock_rate_limit_response = MagicMock()
        mock_rate_limit_response.status_code = 429

        mock_tweepy.return_value.create_tweet.side_effect = [
            TooManyRequests(mock_rate_limit_response),
            mock_response
        ]

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        # Should succeed after retry
        result = handler.create_tweet("Test rate limit retry")
        assert result['success'] is True

    def test_rate_limit_exceeded_max_retries(self, mock_tweepy):
        """Test rate limit exceeded after max retries"""
        # Create mock response for TooManyRequests
        mock_rate_limit_response = MagicMock()
        mock_rate_limit_response.status_code = 429

        mock_tweepy.return_value.create_tweet.side_effect = TooManyRequests(
            mock_rate_limit_response
        )

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        with pytest.raises(RateLimitError):
            handler.create_tweet("Test max retries")

    def test_rate_limit_with_reset_time(self, mock_tweepy):
        """Test rate limit handling with reset time header"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {
            'x-rate-limit-reset': str(int(datetime.utcnow().timestamp()) + 2)
        }

        mock_error = TooManyRequests(mock_response)

        mock_tweepy.return_value.create_tweet.side_effect = [
            mock_error,
            MagicMock(data={'id': '123', 'text': 'Success'})
        ]

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        # Should wait for reset time
        with patch('time.sleep') as mock_sleep:
            result = handler.create_tweet("Test reset time")
            mock_sleep.assert_called()


# ==================== Exponential Backoff Tests ====================

@pytest.mark.unit
class TestExponentialBackoff:
    """Test exponential backoff retry logic"""

    def test_backoff_decorator_success_first_try(self, mock_tweepy):
        """Test decorator with immediate success"""
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        result = handler.create_tweet("Test immediate success")
        assert result['success'] is True

    def test_backoff_decorator_retry_on_error(self, mock_tweepy):
        """Test decorator retries on transient errors"""
        mock_tweepy.return_value.create_tweet.side_effect = [
            TweepyException("Transient error"),
            TweepyException("Another transient error"),
            MagicMock(data={'id': '123', 'text': 'Success'})
        ]

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        with patch('time.sleep'):  # Speed up test
            result = handler.create_tweet("Test retry")
            assert result['success'] is True

    def test_backoff_exponential_delay(self, mock_tweepy):
        """Test exponential increase in delay"""
        mock_tweepy.return_value.create_tweet.side_effect = TweepyException("Error")

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        delays = []

        with patch('time.sleep', side_effect=lambda x: delays.append(x)):
            try:
                handler.create_tweet("Test exponential backoff")
            except:
                pass

        # Verify delays increase exponentially
        assert len(delays) > 0
        if len(delays) >= 2:
            # Each delay should be roughly double the previous (with jitter)
            assert delays[1] > delays[0]

    def test_backoff_max_delay_cap(self, mock_tweepy):
        """Test delay is capped at max_delay"""
        mock_tweepy.return_value.create_tweet.side_effect = TweepyException("Error")

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        delays = []

        with patch('time.sleep', side_effect=lambda x: delays.append(x)):
            try:
                handler.create_tweet("Test max delay")
            except:
                pass

        # No delay should exceed max_delay * 1.5 (accounting for jitter)
        assert all(d <= 90 for d in delays)  # max_delay=60, jitter can add up to 1.5x


# ==================== Error Handling Tests ====================

@pytest.mark.unit
class TestErrorHandling:
    """Test error handling scenarios"""

    def test_unauthorized_error(self, mock_tweepy):
        """Test handling unauthorized errors"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_tweepy.return_value.create_tweet.side_effect = Unauthorized(mock_response)

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        with pytest.raises(AuthenticationError):
            handler.create_tweet("Test unauthorized")

    def test_api_error_max_retries(self, mock_tweepy):
        """Test API error exceeds max retries"""
        mock_tweepy.return_value.create_tweet.side_effect = TweepyException("API Error")

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        with patch('time.sleep'):
            with pytest.raises(Exception):
                handler.create_tweet("Test max retries")


# ==================== Tweet Metrics Tests ====================

@pytest.mark.unit
class TestGetTweetMetrics:
    """Test retrieving tweet metrics"""

    def test_get_tweet_metrics_success(self, mock_tweepy):
        """Test successful metrics retrieval"""
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        metrics = handler.get_tweet_metrics("1234567890123456789")

        assert 'tweet_id' in metrics
        assert 'likes' in metrics
        assert 'retweets' in metrics
        assert metrics['likes'] == 45

    def test_get_tweet_metrics_not_found(self, mock_tweepy):
        """Test metrics for non-existent tweet"""
        mock_tweepy.return_value.get_tweet.return_value.data = None

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        metrics = handler.get_tweet_metrics("999999999")
        assert metrics == {}

    def test_get_tweet_metrics_error(self, mock_tweepy):
        """Test metrics retrieval error"""
        mock_tweepy.return_value.get_tweet.side_effect = TweepyException("Not found")

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        metrics = handler.get_tweet_metrics("invalid_id")
        assert metrics == {}


# ==================== User Metrics Tests ====================

@pytest.mark.unit
class TestGetUserMetrics:
    """Test retrieving user profile metrics"""

    def test_get_user_metrics_success(self, mock_tweepy):
        """Test successful user metrics retrieval"""
        mock_user = MagicMock()
        mock_user.data = MagicMock()
        mock_user.data.username = "test_user"
        mock_user.data.name = "Test User"
        mock_user.data.public_metrics = {
            'followers_count': 1500,
            'following_count': 300,
            'tweet_count': 500,
            'listed_count': 25
        }
        mock_tweepy.return_value.get_me.return_value = mock_user

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        metrics = handler.get_user_metrics()

        assert metrics['username'] == "test_user"
        assert metrics['followers'] == 1500
        assert metrics['tweet_count'] == 500

    def test_get_user_metrics_error(self, mock_tweepy):
        """Test user metrics retrieval error"""
        mock_tweepy.return_value.get_me.side_effect = TweepyException("API Error")

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        metrics = handler.get_user_metrics()
        assert metrics == {}


# ==================== Delete Tweet Tests ====================

@pytest.mark.unit
class TestDeleteTweet:
    """Test tweet deletion"""

    def test_delete_tweet_success(self, mock_tweepy):
        """Test successful tweet deletion"""
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        result = handler.delete_tweet("1234567890")
        assert result is True

    def test_delete_tweet_dry_run(self, mock_tweepy):
        """Test delete tweet in dry-run mode"""
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret",
            dry_run=True
        )

        result = handler.delete_tweet("1234567890")
        assert result is True

    def test_delete_tweet_error(self, mock_tweepy):
        """Test delete tweet error"""
        mock_tweepy.return_value.delete_tweet.side_effect = TweepyException("Delete failed")

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        result = handler.delete_tweet("invalid_id")
        assert result is False


# ==================== Search Tests ====================

@pytest.mark.unit
class TestSearchTweets:
    """Test tweet search functionality"""

    def test_search_recent_tweets_success(self, mock_tweepy):
        """Test successful tweet search"""
        mock_tweets = MagicMock()
        mock_tweet_data = MagicMock()
        mock_tweet_data.id = "123"
        mock_tweet_data.text = "Test tweet"
        mock_tweet_data.created_at = datetime.utcnow()
        mock_tweet_data.public_metrics = {'like_count': 10}

        mock_tweets.data = [mock_tweet_data]
        mock_tweepy.return_value.search_recent_tweets.return_value = mock_tweets

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        results = handler.search_recent_tweets("AI research", max_results=10)

        assert len(results) == 1
        assert results[0]['id'] == "123"
        assert results[0]['text'] == "Test tweet"

    def test_search_with_max_results(self, mock_tweepy):
        """Test search respects max_results parameter"""
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        # Request more than allowed (100 is max)
        handler.search_recent_tweets("test", max_results=150)

        # Verify it was capped at 100
        call_args = mock_tweepy.return_value.search_recent_tweets.call_args
        assert call_args[1]['max_results'] == 100

    def test_search_error(self, mock_tweepy):
        """Test search error handling"""
        mock_tweepy.return_value.search_recent_tweets.side_effect = TweepyException("Search failed")

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        results = handler.search_recent_tweets("test query")
        assert results == []


# ==================== Credential Verification Tests ====================

@pytest.mark.unit
class TestVerifyCredentials:
    """Test credential verification"""

    def test_verify_credentials_success(self, mock_tweepy):
        """Test successful credential verification"""
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        result = handler.verify_credentials()
        assert result is True

    def test_verify_credentials_failure(self, mock_tweepy):
        """Test failed credential verification"""
        mock_tweepy.return_value.get_me.side_effect = TweepyException("Invalid credentials")

        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        result = handler.verify_credentials()
        assert result is False


# ==================== RateLimitTracker Tests ====================

@pytest.mark.unit
class TestRateLimitTracker:
    """Test RateLimitTracker functionality"""

    def test_init_free_tier(self):
        """Test initialization with free tier"""
        tracker = RateLimitTracker(tier='free')

        assert tracker.tier == 'free'
        assert tracker.limits == TWITTER_RATE_LIMITS['free']
        assert tracker.tweets_today == 0
        assert tracker.tweets_month == 0

    def test_init_basic_tier(self):
        """Test initialization with basic tier"""
        tracker = RateLimitTracker(tier='basic')

        assert tracker.tier == 'basic'
        assert tracker.limits['tweets_per_24h'] == 100

    def test_init_pro_tier(self):
        """Test initialization with pro tier"""
        tracker = RateLimitTracker(tier='pro')

        assert tracker.tier == 'pro'
        assert tracker.limits['tweets_per_24h'] == 300

    def test_can_post_within_limits(self):
        """Test can_post returns True when within limits"""
        tracker = RateLimitTracker(tier='basic')

        assert tracker.can_post() is True

    def test_can_post_daily_limit_reached(self):
        """Test can_post returns False at daily limit"""
        tracker = RateLimitTracker(tier='free')
        tracker.tweets_today = 17  # Free tier limit

        assert tracker.can_post() is False

    def test_can_post_monthly_limit_reached(self):
        """Test can_post returns False at monthly limit"""
        tracker = RateLimitTracker(tier='free')
        tracker.tweets_month = 500  # Free tier limit

        assert tracker.can_post() is False

    def test_record_post(self):
        """Test recording a post"""
        tracker = RateLimitTracker(tier='basic')

        tracker.record_post()

        assert tracker.tweets_today == 1
        assert tracker.tweets_month == 1

    def test_reset_daily(self):
        """Test daily counter reset"""
        tracker = RateLimitTracker(tier='basic')
        tracker.tweets_today = 50
        tracker.tweets_month = 50

        tracker.reset_daily()

        assert tracker.tweets_today == 0
        assert tracker.tweets_month == 50  # Month not reset

    def test_get_status(self):
        """Test getting tracker status"""
        tracker = RateLimitTracker(tier='basic')
        tracker.tweets_today = 10
        tracker.tweets_month = 50

        status = tracker.get_status()

        assert status['tier'] == 'basic'
        assert status['tweets_today'] == 10
        assert status['tweets_month'] == 50
        assert status['daily_remaining'] == 90
        assert status['monthly_remaining'] == 2950

    def test_multiple_posts_tracking(self):
        """Test tracking multiple posts"""
        tracker = RateLimitTracker(tier='basic')

        for i in range(10):
            tracker.record_post()

        assert tracker.tweets_today == 10
        assert tracker.tweets_month == 10


# ==================== Integration Tests ====================

@pytest.mark.integration
class TestTwitterHandlerIntegration:
    """Integration tests for TwitterHandler"""

    def test_full_tweet_lifecycle(self, mock_tweepy):
        """Test complete tweet lifecycle: create -> get metrics -> delete"""
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        # Create tweet
        result = handler.create_tweet("Integration test tweet")
        assert result['success'] is True
        tweet_id = result['tweet_id']

        # Get metrics
        metrics = handler.get_tweet_metrics(tweet_id)
        assert 'likes' in metrics

        # Delete tweet
        deleted = handler.delete_tweet(tweet_id)
        assert deleted is True

    def test_rate_limit_tracker_integration(self, mock_tweepy):
        """Test rate limit tracker with actual posting"""
        handler = TwitterHandler(
            api_key="test_key",
            api_secret="test_secret",
            access_token="test_token",
            access_secret="test_token_secret"
        )

        tracker = RateLimitTracker(tier='free')

        # Post multiple tweets
        for i in range(5):
            if tracker.can_post():
                result = handler.create_tweet(f"Test tweet {i}")
                assert result['success'] is True
                tracker.record_post()

        assert tracker.tweets_today == 5
        assert tracker.tweets_month == 5


# ==================== API Tests (marked for manual run) ====================

@pytest.mark.api
class TestTwitterHandlerAPIIntegration:
    """Tests that hit real Twitter API (require valid credentials)"""

    @pytest.mark.skip(reason="Requires valid Twitter API credentials")
    def test_real_tweet_creation(self):
        """Test creating a real tweet (requires credentials)"""
        import os

        handler = TwitterHandler(
            api_key=os.getenv('TWITTER_API_KEY'),
            api_secret=os.getenv('TWITTER_API_SECRET'),
            access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
            access_secret=os.getenv('TWITTER_ACCESS_SECRET')
        )

        result = handler.create_tweet("Test tweet from pytest")
        assert result['success'] is True
        print(f"Tweet URL: {result['url']}")

    @pytest.mark.skip(reason="Requires valid Twitter API credentials")
    def test_real_credential_verification(self):
        """Test verifying real credentials"""
        import os

        handler = TwitterHandler(
            api_key=os.getenv('TWITTER_API_KEY'),
            api_secret=os.getenv('TWITTER_API_SECRET'),
            access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
            access_secret=os.getenv('TWITTER_ACCESS_SECRET')
        )

        assert handler.verify_credentials() is True
