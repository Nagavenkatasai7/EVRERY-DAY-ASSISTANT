"""
Twitter/X OAuth 2.0 Handler
Supports OAuth 2.0 Client Credentials for app-level access
"""

import requests
import base64
from typing import Dict, Optional
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger(__name__)


class TwitterOAuth2Handler:
    """
    Twitter API v2 handler using OAuth 2.0

    Note: OAuth 2.0 Client Credentials flow provides app-level access.
    For user context (posting tweets), you need OAuth 2.0 Authorization Code flow.
    """

    def __init__(self, client_id: str, client_secret: str, bearer_token: Optional[str] = None):
        """
        Initialize Twitter OAuth 2.0 handler

        Args:
            client_id: OAuth 2.0 Client ID
            client_secret: OAuth 2.0 Client Secret
            bearer_token: Pre-generated Bearer Token (if available)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.bearer_token = bearer_token
        self.access_token = None
        self.token_expires_at = None

        logger.info("Twitter OAuth 2.0 handler initialized")

    def get_bearer_token(self) -> Optional[str]:
        """
        Get OAuth 2.0 Bearer Token using Client Credentials flow

        Note: This provides app-level access, NOT user context.
        For posting tweets, you need user-level Bearer Token.

        Returns:
            Bearer token string or None if failed
        """
        try:
            # Create Basic Auth header
            credentials = f"{self.client_id}:{self.client_secret}"
            b64_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                "Authorization": f"Basic {b64_credentials}",
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
            }

            data = {"grant_type": "client_credentials"}

            logger.info("🔄 Requesting Twitter bearer token...")
            logger.info(f"   Client ID: {self.client_id}")
            logger.info(f"   Grant type: client_credentials")

            response = requests.post(
                "https://api.twitter.com/oauth2/token",
                headers=headers,
                data=data,
                timeout=10
            )

            logger.info(f"📡 Twitter token response: {response.status_code}")

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")

                # Set expiration (typically 2 hours) with 5-minute buffer
                expires_in = token_data.get("expires_in", 7200)
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)

                logger.info("✅ Twitter bearer token obtained successfully")
                logger.info(f"   Token expires in: {expires_in} seconds ({expires_in / 3600:.1f} hours)")
                logger.info(f"   Token expiry: {self.token_expires_at.isoformat()}")
                logger.warning("⚠️ OAuth 2.0 Client Credentials provides app-level access only")
                logger.warning("⚠️ For posting tweets, you need OAuth 1.0a or OAuth 2.0 Authorization Code flow")
                return self.access_token
            else:
                error_data = response.json() if response.text else {}
                error_type = error_data.get("errors", [{}])[0].get("code", "unknown") if error_data.get("errors") else "unknown"
                error_message = error_data.get("errors", [{}])[0].get("message", response.text) if error_data.get("errors") else response.text

                logger.error(f"❌ Failed to get Twitter bearer token")
                logger.error(f"   Status: {response.status_code}")
                logger.error(f"   Error code: {error_type}")
                logger.error(f"   Error message: {error_message}")
                logger.error(f"   Full response: {response.text}")

                # Specific error handling
                if response.status_code == 403:
                    if "authenticity_token_error" in str(error_message):
                        logger.error("   💡 Hint: Unable to verify credentials")
                        logger.error("   💡 Check: TWITTER_CLIENT_ID and TWITTER_CLIENT_SECRET in .env")
                        logger.error("   💡 Action: Verify credentials in Twitter Developer Portal")
                    else:
                        logger.error("   💡 Hint: Access forbidden - check app permissions")
                        logger.error("   💡 Required: Read and Write permissions in Twitter Developer Portal")
                elif response.status_code == 401:
                    logger.error("   💡 Hint: Authentication failed - invalid credentials")
                    logger.error("   💡 Action: Regenerate Client ID and Secret in Twitter Developer Portal")

                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error getting bearer token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error getting bearer token: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token"""
        # Use pre-configured bearer token if available
        if self.bearer_token:
            self.access_token = self.bearer_token
            return True

        # Check if current token is still valid
        if self.access_token and self.token_expires_at:
            if datetime.utcnow() < self.token_expires_at - timedelta(minutes=5):
                return True

        # Get new token
        token = self.get_bearer_token()
        return token is not None

    def post_tweet(self, content: str) -> Optional[str]:
        """
        Post a tweet using OAuth 2.0

        Args:
            content: Tweet text (max 280 characters)

        Returns:
            Tweet ID if successful, None otherwise
        """
        if not self.ensure_valid_token():
            logger.error("❌ Failed to obtain valid access token for posting")
            logger.error("   💡 Hint: Check Twitter OAuth credentials in .env")
            return None

        # Validate content
        if len(content) > 280:
            logger.error(f"❌ Tweet too long: {len(content)} characters (max 280)")
            return None

        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            payload = {"text": content}

            logger.info("🔄 Posting tweet to Twitter...")
            logger.info(f"   Content length: {len(content)} chars")
            logger.info(f"   Content preview: {content[:60]}...")
            logger.info(f"   Token length: {len(self.access_token)} chars")

            response = requests.post(
                "https://api.twitter.com/2/tweets",
                headers=headers,
                json=payload,
                timeout=10
            )

            logger.info(f"📡 Twitter post response: {response.status_code}")

            if response.status_code == 201:
                tweet_data = response.json()
                tweet_id = tweet_data.get("data", {}).get("id")
                logger.info(f"✅ Tweet posted successfully")
                logger.info(f"   Tweet ID: {tweet_id}")
                return tweet_id
            else:
                error_data = response.json() if response.text else {}
                error_type = error_data.get("errors", [{}])[0].get("title", "unknown") if error_data.get("errors") else "unknown"
                error_message = error_data.get("errors", [{}])[0].get("detail", response.text) if error_data.get("errors") else response.text
                error_type_code = error_data.get("errors", [{}])[0].get("type", "") if error_data.get("errors") else ""

                logger.error(f"❌ Failed to post tweet")
                logger.error(f"   Status: {response.status_code}")
                logger.error(f"   Error type: {error_type}")
                logger.error(f"   Error message: {error_message}")
                logger.error(f"   Full response: {response.text}")

                # Specific error handling
                if response.status_code == 401:
                    logger.error("   💡 Hint: Authentication failed - invalid or expired token")
                    logger.error("   💡 Action: Check OAuth credentials and token validity")
                elif response.status_code == 403:
                    if "Client" in str(error_message) or "app" in str(error_message).lower():
                        logger.error("   💡 Hint: OAuth 2.0 Client Credentials cannot post tweets")
                        logger.error("   💡 Required: OAuth 1.0a or OAuth 2.0 Authorization Code flow")
                        logger.error("   💡 Action: Use Twitter OAuth 1.0a handler instead")
                    else:
                        logger.error("   💡 Hint: Insufficient permissions")
                        logger.error("   💡 Required: Read and Write permissions in Twitter Developer Portal")
                        logger.error("   💡 Action: Change app permissions and regenerate tokens")
                elif response.status_code == 400:
                    logger.error("   💡 Hint: Invalid request - check tweet content format")
                elif response.status_code == 429:
                    logger.error("   💡 Hint: Rate limit exceeded")
                    logger.error("   💡 Action: Wait before retrying")

                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error posting tweet: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error posting tweet: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def get_tweet(self, tweet_id: str) -> Optional[Dict]:
        """Get tweet data by ID"""
        if not self.ensure_valid_token():
            return None

        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}

            response = requests.get(
                f"https://api.twitter.com/2/tweets/{tweet_id}",
                headers=headers,
                params={"tweet.fields": "created_at,public_metrics"},
                timeout=10
            )

            if response.status_code == 200:
                return response.json().get("data")
            else:
                logger.error(f"Failed to get tweet: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting tweet: {str(e)}")
            return None

    def delete_tweet(self, tweet_id: str) -> bool:
        """Delete a tweet"""
        if not self.ensure_valid_token():
            return False

        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}

            response = requests.delete(
                f"https://api.twitter.com/2/tweets/{tweet_id}",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"✅ Tweet deleted: {tweet_id}")
                return True
            else:
                logger.error(f"Failed to delete tweet: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error deleting tweet: {str(e)}")
            return False
