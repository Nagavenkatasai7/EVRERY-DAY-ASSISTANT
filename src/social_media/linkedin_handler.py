"""
LinkedIn API Handler for Automated Posting
Uses LinkedIn API v2 with OAuth 2.0

⚠️ WARNING: Automated posting to LinkedIn may violate their Terms of Service.
LinkedIn's User Agreement prohibits automated posting without explicit permission.
Use this handler at your own risk and ensure compliance with LinkedIn's policies.
"""

import requests
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from utils.logger import get_logger
from utils.exceptions import AuthenticationError, RateLimitError

logger = get_logger(__name__)


class LinkedInHandler:
    """
    LinkedIn API v2 handler using OAuth 2.0

    ⚠️ COMPLIANCE WARNING:
    - This handler is for educational/research purposes
    - Automated posting may violate LinkedIn Terms of Service
    - LinkedIn API requires approval for posting capabilities
    - Use only with proper authorization and at your own risk
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: Optional[str] = None,
        dry_run: bool = False
    ):
        """
        Initialize LinkedIn API handler

        Args:
            client_id: LinkedIn OAuth 2.0 Client ID
            client_secret: LinkedIn OAuth 2.0 Client Secret
            access_token: Pre-generated access token (if available)
            dry_run: If True, log actions without posting
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.token_expires_at = None
        self.dry_run = dry_run
        self.person_urn = None  # LinkedIn user URN

        logger.info("LinkedIn API handler initialized")
        logger.warning("⚠️ Automated LinkedIn posting may violate Terms of Service")

    def generate_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        scope: str = "openid profile email w_member_social"
    ) -> str:
        """
        Generate LinkedIn OAuth 2.0 authorization URL for user to visit

        CRITICAL: LinkedIn migrated to OpenID Connect - must include openid scope

        Args:
            redirect_uri: URL to redirect back to after authorization
            state: Random string for CSRF protection
            scope: Space-separated list of permissions
                   Default: "openid profile email w_member_social"
                   - openid: Required for OpenID Connect
                   - profile: Basic profile info
                   - email: Email address
                   - w_member_social: Post on behalf of user

        Returns:
            Authorization URL string

        Example:
            >>> handler = LinkedInHandler(client_id, client_secret)
            >>> state = secrets.token_urlsafe(32)
            >>> auth_url = handler.generate_authorization_url(
            ...     redirect_uri="http://localhost:8502/callback",
            ...     state=state
            ... )
            >>> # Direct user to auth_url in browser
        """
        import urllib.parse

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scope
        }

        base_url = "https://www.linkedin.com/oauth/v2/authorization"
        query_string = urllib.parse.urlencode(params)

        auth_url = f"{base_url}?{query_string}"

        logger.info(f"✅ Generated LinkedIn authorization URL")
        logger.info(f"   Scopes requested: {scope}")
        logger.info(f"   Redirect URI: {redirect_uri}")
        logger.info(f"   State: {state[:10]}...")

        return auth_url

    def get_access_token(self, authorization_code: str, redirect_uri: str) -> Optional[str]:
        """
        Exchange authorization code for access token

        Args:
            authorization_code: Code from OAuth authorization flow
            redirect_uri: Redirect URI used in authorization request

        Returns:
            Access token string or None if failed
        """
        try:
            url = "https://www.linkedin.com/oauth/v2/accessToken"

            data = {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": redirect_uri,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            logger.info("🔄 Requesting LinkedIn access token...")
            logger.info(f"   Redirect URI: {redirect_uri}")
            logger.info(f"   Client ID: {self.client_id}")
            logger.info(f"   Auth code length: {len(authorization_code)} chars")

            response = requests.post(url, data=data, headers=headers, timeout=10)

            logger.info(f"📡 LinkedIn token response: {response.status_code}")

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")

                # Set expiration (typically 60 days for LinkedIn) with 5-minute buffer
                expires_in = token_data.get("expires_in", 5184000)
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)

                logger.info("✅ LinkedIn access token obtained successfully")
                logger.info(f"   Token expires in: {expires_in} seconds ({expires_in / 86400:.1f} days)")
                logger.info(f"   Token expiry: {self.token_expires_at.isoformat()}")
                return self.access_token
            else:
                error_data = response.json() if response.text else {}
                error_type = error_data.get("error", "unknown")
                error_desc = error_data.get("error_description", response.text)

                logger.error(f"❌ Failed to get LinkedIn access token")
                logger.error(f"   Status: {response.status_code}")
                logger.error(f"   Error type: {error_type}")
                logger.error(f"   Error description: {error_desc}")
                logger.error(f"   Full response: {response.text}")

                # Specific error handling
                if error_type == "invalid_grant":
                    logger.error("   💡 Hint: Authorization code may be expired or already used")
                elif error_type == "invalid_client":
                    logger.error("   💡 Hint: Check LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env")
                elif error_type == "redirect_uri_mismatch":
                    logger.error(f"   💡 Hint: Redirect URI mismatch. Check LinkedIn Developer Portal settings")

                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error getting access token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error getting access token: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: LinkedIn refresh token

        Returns:
            New access token or None if failed
        """
        try:
            url = "https://www.linkedin.com/oauth/v2/accessToken"

            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            response = requests.post(url, data=data, headers=headers, timeout=10)

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")

                expires_in = token_data.get("expires_in", 5184000)
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                logger.info("✅ Access token refreshed successfully")
                return self.access_token
            else:
                logger.error(f"Failed to refresh token: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            return None

    def get_user_profile(self) -> Optional[Dict]:
        """
        Get authenticated user's LinkedIn profile

        Returns:
            Dict with user profile data including person URN
        """
        if not self.access_token:
            logger.error("❌ No access token available for profile request")
            logger.error("   💡 Hint: Complete OAuth authorization first")
            return None

        try:
            url = "https://api.linkedin.com/v2/userinfo"  # OpenID Connect endpoint

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            logger.info("🔄 Fetching LinkedIn user profile...")
            logger.info(f"   Endpoint: {url}")
            logger.info(f"   Token length: {len(self.access_token)} chars")

            response = requests.get(url, headers=headers, timeout=10)

            logger.info(f"📡 LinkedIn profile response: {response.status_code}")

            if response.status_code == 200:
                profile_data = response.json()

                # Store person URN for posting (from 'sub' field in OpenID Connect)
                person_id = profile_data.get("sub")
                if person_id:
                    self.person_urn = f"urn:li:person:{person_id}"
                    logger.info(f"✅ Retrieved LinkedIn user profile")
                    logger.info(f"   Person URN: {self.person_urn}")
                    logger.info(f"   Name: {profile_data.get('name', 'N/A')}")
                    logger.info(f"   Email: {profile_data.get('email', 'N/A')}")
                else:
                    logger.warning("⚠️ Profile retrieved but no 'sub' field found")
                    logger.info(f"   Available fields: {list(profile_data.keys())}")

                return profile_data
            else:
                error_data = response.json() if response.text else {}
                error_code = error_data.get("serviceErrorCode", error_data.get("status", "unknown"))
                error_message = error_data.get("message", response.text)

                logger.error(f"❌ Failed to get LinkedIn profile")
                logger.error(f"   Status: {response.status_code}")
                logger.error(f"   Error code: {error_code}")
                logger.error(f"   Error message: {error_message}")
                logger.error(f"   Full response: {response.text}")

                # Specific error handling
                if response.status_code == 401:
                    logger.error("   💡 Hint: Access token is invalid or expired")
                elif response.status_code == 403:
                    logger.error("   💡 Hint: Token lacks required scopes (openid, profile, email)")
                    logger.error("   💡 Action: Re-authorize with OpenID Connect scopes")
                elif error_code == 100:  # ACCESS_DENIED
                    logger.error("   💡 Hint: Check LinkedIn Developer Portal products and scopes")
                    logger.error("   💡 Required: 'Sign In with LinkedIn using OpenID Connect'")

                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error getting profile: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error getting profile: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def create_post(self, content: str, visibility: str = "PUBLIC") -> Optional[str]:
        """
        Create a LinkedIn post

        ⚠️ WARNING: This may violate LinkedIn Terms of Service

        Args:
            content: Post text (max 3000 characters)
            visibility: Post visibility ("PUBLIC" or "CONNECTIONS")

        Returns:
            Post URN if successful, None otherwise
        """
        if self.dry_run:
            logger.info(f"DRY RUN: Would post to LinkedIn: {content[:50]}...")
            return "urn:li:share:dry_run_12345"

        if not self.access_token:
            logger.error("❌ No access token available for posting")
            logger.error("   💡 Hint: Complete OAuth authorization first")
            return None

        # Get user profile if we don't have person_urn
        if not self.person_urn:
            logger.info("🔄 Person URN not set, fetching user profile...")
            profile = self.get_user_profile()
            if not profile:
                logger.error("❌ Failed to get user profile for posting")
                return None

        # Validate content length
        if len(content) > 3000:
            logger.error(f"❌ Post too long: {len(content)} characters (max 3000)")
            return None

        try:
            url = "https://api.linkedin.com/v2/ugcPosts"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }

            # Build post payload
            payload = {
                "author": self.person_urn,
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": content
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": visibility
                }
            }

            logger.info("🔄 Creating LinkedIn post...")
            logger.info(f"   Author URN: {self.person_urn}")
            logger.info(f"   Content length: {len(content)} chars")
            logger.info(f"   Visibility: {visibility}")
            logger.info(f"   Content preview: {content[:80]}...")

            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=10
            )

            logger.info(f"📡 LinkedIn post response: {response.status_code}")

            if response.status_code == 201:
                # Extract post ID from response headers
                post_id = response.headers.get("x-restli-id")
                post_urn = f"urn:li:share:{post_id}" if post_id else None

                logger.info(f"✅ Posted to LinkedIn successfully")
                logger.info(f"   Post URN: {post_urn}")
                logger.warning("⚠️ This automated post may violate LinkedIn ToS")

                return post_urn
            else:
                error_data = response.json() if response.text else {}
                error_code = error_data.get("serviceErrorCode", error_data.get("status", "unknown"))
                error_message = error_data.get("message", response.text)

                logger.error(f"❌ Failed to create LinkedIn post")
                logger.error(f"   Status: {response.status_code}")
                logger.error(f"   Error code: {error_code}")
                logger.error(f"   Error message: {error_message}")
                logger.error(f"   Full response: {response.text}")

                # Specific error handling
                if response.status_code == 401:
                    logger.error("   💡 Hint: Access token is invalid or expired")
                elif response.status_code == 403:
                    logger.error("   💡 Hint: Token lacks w_member_social scope")
                    logger.error("   💡 Action: Check LinkedIn Developer Portal permissions")
                    logger.error("   💡 Required: 'Share on LinkedIn' product with w_member_social scope")
                elif response.status_code == 422:
                    logger.error("   💡 Hint: Invalid request payload")
                    logger.error(f"   💡 Check: Author URN format, content length, visibility value")

                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error creating post: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error creating post: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def get_post_statistics(self, post_urn: str) -> Optional[Dict]:
        """
        Get engagement statistics for a post

        Args:
            post_urn: LinkedIn post URN

        Returns:
            Dict with engagement metrics
        """
        if not self.access_token:
            logger.error("No access token available")
            return None

        try:
            # Extract share ID from URN
            share_id = post_urn.split(":")[-1]

            url = f"https://api.linkedin.com/v2/socialActions/{share_id}"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                stats = response.json()

                return {
                    "post_urn": post_urn,
                    "likes": stats.get("likeCount", 0),
                    "comments": stats.get("commentCount", 0),
                    "shares": stats.get("shareCount", 0),
                    "impressions": stats.get("impressionCount", 0)
                }
            else:
                logger.error(f"Failed to get statistics: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting post statistics: {str(e)}")
            return None

    def delete_post(self, post_urn: str) -> bool:
        """
        Delete a LinkedIn post

        Args:
            post_urn: Post URN to delete

        Returns:
            True if successful, False otherwise
        """
        if self.dry_run:
            logger.info(f"DRY RUN: Would delete post {post_urn}")
            return True

        if not self.access_token:
            logger.error("No access token available")
            return False

        try:
            url = f"https://api.linkedin.com/v2/ugcPosts/{post_urn}"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "X-Restli-Protocol-Version": "2.0.0"
            }

            response = requests.delete(url, headers=headers, timeout=10)

            if response.status_code == 204:
                logger.info(f"✅ Deleted LinkedIn post: {post_urn}")
                return True
            else:
                logger.error(f"Failed to delete post: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error deleting post: {str(e)}")
            return False

    def verify_credentials(self) -> bool:
        """
        Verify that access token is valid

        Returns:
            True if credentials valid, False otherwise
        """
        try:
            profile = self.get_user_profile()
            if profile:
                logger.info("✅ LinkedIn credentials verified")
                return True
            else:
                logger.error("❌ LinkedIn credential verification failed")
                return False
        except Exception as e:
            logger.error(f"❌ Credential verification error: {str(e)}")
            return False


# LinkedIn API rate limits
LINKEDIN_RATE_LIMITS = {
    "posts_per_day": 150,  # Conservative estimate
    "posts_per_hour": 25,
    "api_calls_per_day": 5000
}


class LinkedInRateLimitTracker:
    """Tracks LinkedIn API usage to stay within rate limits"""

    def __init__(self):
        """Initialize rate limit tracker"""
        self.posts_today = 0
        self.posts_hour = 0
        self.api_calls_today = 0
        self.last_post_time = None
        self.hour_reset = datetime.utcnow()
        self.day_reset = datetime.utcnow()

    def can_post(self) -> bool:
        """Check if posting is allowed within rate limits"""
        now = datetime.utcnow()

        # Reset hourly counter
        if (now - self.hour_reset).total_seconds() >= 3600:
            self.posts_hour = 0
            self.hour_reset = now

        # Reset daily counter
        if (now - self.day_reset).total_seconds() >= 86400:
            self.posts_today = 0
            self.api_calls_today = 0
            self.day_reset = now

        # Check limits
        if self.posts_hour >= LINKEDIN_RATE_LIMITS["posts_per_hour"]:
            logger.warning(f"Hourly post limit reached: {self.posts_hour}/{LINKEDIN_RATE_LIMITS['posts_per_hour']}")
            return False

        if self.posts_today >= LINKEDIN_RATE_LIMITS["posts_per_day"]:
            logger.warning(f"Daily post limit reached: {self.posts_today}/{LINKEDIN_RATE_LIMITS['posts_per_day']}")
            return False

        # Enforce minimum delay between posts (2 minutes)
        if self.last_post_time:
            time_since_last = (now - self.last_post_time).total_seconds()
            if time_since_last < 120:
                logger.warning(f"Too soon since last post ({time_since_last:.0f}s). Wait at least 2 minutes.")
                return False

        return True

    def record_post(self):
        """Record a posted update"""
        self.posts_today += 1
        self.posts_hour += 1
        self.api_calls_today += 1
        self.last_post_time = datetime.utcnow()

    def record_api_call(self):
        """Record an API call"""
        self.api_calls_today += 1

    def get_status(self) -> Dict:
        """Get current usage status"""
        return {
            "posts_today": self.posts_today,
            "posts_hour": self.posts_hour,
            "api_calls_today": self.api_calls_today,
            "hourly_remaining": LINKEDIN_RATE_LIMITS["posts_per_hour"] - self.posts_hour,
            "daily_remaining": LINKEDIN_RATE_LIMITS["posts_per_day"] - self.posts_today
        }
