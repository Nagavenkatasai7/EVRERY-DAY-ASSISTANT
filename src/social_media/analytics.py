"""
Social Media Analytics Collection System

Comprehensive analytics collection and reporting for social media automation platform.
Collects metrics from Twitter API, calculates derived metrics, and generates reports.

Features:
- Post-level metrics collection (impressions, engagement, clicks)
- User-level analytics aggregation
- Recruiter engagement tracking
- Best posting times analysis
- Weekly performance reports
- Time-series trend analysis

References:
- Twitter API v2 Metrics: https://developer.twitter.com/en/docs/twitter-api/metrics
- Engagement Rate Calculations: Industry standard (interactions/impressions)
"""

import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from statistics import mean, median
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from src.social_media.models import (
    Post, PostAnalytics, Analytics, User, Platform, PostStatus,
    DatabaseManager
)
from src.social_media.twitter_handler import TwitterHandler
from utils.logger import get_logger
from utils.exceptions import APIError, RateLimitError

logger = get_logger(__name__)


class AnalyticsCollector:
    """
    Collect and analyze social media metrics with comprehensive tracking

    This class provides methods to:
    - Fetch metrics from Twitter API
    - Calculate engagement rates and derived metrics
    - Track recruiter-specific engagement
    - Identify optimal posting times
    - Generate performance reports
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        twitter_handler: Optional[TwitterHandler] = None
    ):
        """
        Initialize analytics collector

        Args:
            db_manager: Database manager instance for data persistence
            twitter_handler: Optional TwitterHandler for API calls
        """
        self.db_manager = db_manager
        self.twitter_handler = twitter_handler
        self.logger = logger

    def collect_post_metrics(self, post_id: int) -> Dict:
        """
        Collect metrics for a specific post from Twitter API

        Fetches latest engagement metrics from Twitter API and returns
        structured data for storage.

        Args:
            post_id: Internal database post ID

        Returns:
            Dict containing:
                - success: bool
                - metrics: Dict with impressions, likes, retweets, replies, quotes
                - error: Optional error message

        Raises:
            APIError: If Twitter API call fails
            RateLimitError: If rate limit is exceeded
        """
        session = self.db_manager.get_session()

        try:
            # Get post from database
            post = session.query(Post).filter(Post.id == post_id).first()

            if not post:
                self.logger.error(f"Post {post_id} not found in database")
                return {
                    'success': False,
                    'error': 'Post not found',
                    'metrics': {}
                }

            # Check if post has been published
            if post.status != PostStatus.PUBLISHED or not post.external_post_id:
                self.logger.warning(f"Post {post_id} not published or missing external ID")
                return {
                    'success': False,
                    'error': 'Post not published or missing external ID',
                    'metrics': {}
                }

            # Fetch metrics from Twitter API
            if not self.twitter_handler:
                self.logger.warning("No Twitter handler available, returning mock data")
                return {
                    'success': False,
                    'error': 'No Twitter handler configured',
                    'metrics': {}
                }

            try:
                metrics_data = self.twitter_handler.get_tweet_metrics(post.external_post_id)

                if not metrics_data:
                    self.logger.warning(f"No metrics returned for tweet {post.external_post_id}")
                    return {
                        'success': False,
                        'error': 'No metrics available',
                        'metrics': {}
                    }

                # Structure metrics
                metrics = {
                    'impressions': metrics_data.get('impressions', 0),
                    'likes': metrics_data.get('likes', 0),
                    'retweets': metrics_data.get('retweets', 0),
                    'replies': metrics_data.get('replies', 0),
                    'quotes': metrics_data.get('quotes', 0),
                    'url_clicks': 0,  # Not available in public metrics
                    'profile_clicks': 0,  # Not available in public metrics
                    'media_views': 0,  # Not available in public metrics
                }

                self.logger.info(f"Collected metrics for post {post_id}: {metrics}")

                return {
                    'success': True,
                    'metrics': metrics,
                    'collected_at': datetime.utcnow()
                }

            except RateLimitError as e:
                self.logger.error(f"Rate limit exceeded while fetching metrics: {str(e)}")
                return {
                    'success': False,
                    'error': f'Rate limit exceeded: {str(e)}',
                    'error_type': 'rate_limit',
                    'metrics': {}
                }

            except APIError as e:
                self.logger.error(f"API error fetching metrics: {str(e)}")
                return {
                    'success': False,
                    'error': str(e),
                    'metrics': {}
                }

        except Exception as e:
            self.logger.error(f"Error collecting post metrics: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'metrics': {}
            }
        finally:
            session.close()

    def calculate_engagement_rate(self, post_id: int) -> float:
        """
        Calculate engagement rate for a post

        Engagement Rate = (likes + retweets + replies + quotes) / impressions * 100

        Args:
            post_id: Internal database post ID

        Returns:
            Engagement rate as percentage (0.0 - 100.0)
            Returns 0.0 if no impressions or analytics data
        """
        session = self.db_manager.get_session()

        try:
            # Get latest analytics for post
            analytics = session.query(PostAnalytics).filter(
                PostAnalytics.post_id == post_id
            ).order_by(PostAnalytics.snapshot_time.desc()).first()

            if not analytics or not analytics.impressions or analytics.impressions == 0:
                self.logger.debug(f"No analytics or zero impressions for post {post_id}")
                return 0.0

            # Calculate total engagements
            total_engagements = (
                analytics.likes +
                analytics.comments +  # replies
                analytics.retweets +
                analytics.shares  # quotes/retweets
            )

            # Calculate rate
            engagement_rate = (total_engagements / analytics.impressions) * 100

            self.logger.debug(
                f"Post {post_id}: {total_engagements} engagements / "
                f"{analytics.impressions} impressions = {engagement_rate:.2f}%"
            )

            return round(engagement_rate, 2)

        except Exception as e:
            self.logger.error(f"Error calculating engagement rate: {str(e)}")
            return 0.0
        finally:
            session.close()

    def update_post_analytics(self, post_id: int) -> Optional[PostAnalytics]:
        """
        Fetch latest metrics and update PostAnalytics table

        This method:
        1. Collects metrics from Twitter API
        2. Calculates derived metrics (engagement rate, weighted score)
        3. Creates new PostAnalytics snapshot
        4. Returns the created analytics record

        Args:
            post_id: Internal database post ID

        Returns:
            PostAnalytics object if successful, None otherwise
        """
        session = self.db_manager.get_session()

        try:
            # Collect metrics from API
            result = self.collect_post_metrics(post_id)

            if not result['success']:
                self.logger.warning(f"Failed to collect metrics for post {post_id}")
                return None

            metrics = result['metrics']

            # Get post to calculate hours since published
            post = session.query(Post).filter(Post.id == post_id).first()
            if not post or not post.published_time:
                self.logger.error(f"Post {post_id} not found or not published")
                return None

            hours_since_published = int(
                (datetime.utcnow() - post.published_time).total_seconds() / 3600
            )

            # Calculate engagement rate
            impressions = metrics.get('impressions', 0)
            total_engagements = (
                metrics.get('likes', 0) +
                metrics.get('retweets', 0) +
                metrics.get('replies', 0) +
                metrics.get('quotes', 0)
            )

            engagement_rate = 0.0
            if impressions > 0:
                engagement_rate = (total_engagements / impressions) * 100

            # Calculate weighted engagement score
            # Weight: likes=1, retweets=2, replies=3, quotes=2
            weighted_score = (
                metrics.get('likes', 0) * 1.0 +
                metrics.get('retweets', 0) * 2.0 +
                metrics.get('replies', 0) * 3.0 +
                metrics.get('quotes', 0) * 2.0
            )

            # Create analytics snapshot
            analytics = PostAnalytics(
                post_id=post_id,
                impressions=metrics.get('impressions', 0),
                views=metrics.get('impressions', 0),  # Use impressions as views
                likes=metrics.get('likes', 0),
                comments=metrics.get('replies', 0),
                shares=metrics.get('quotes', 0),
                retweets=metrics.get('retweets', 0),
                clicks=metrics.get('url_clicks', 0),
                engagement_rate=engagement_rate,
                weighted_engagement_score=weighted_score,
                snapshot_time=datetime.utcnow(),
                hours_since_published=hours_since_published
            )

            session.add(analytics)
            session.commit()
            session.refresh(analytics)

            self.logger.info(
                f"Created analytics snapshot for post {post_id}: "
                f"{total_engagements} engagements, {engagement_rate:.2f}% rate"
            )

            return analytics

        except Exception as e:
            self.logger.error(f"Error updating post analytics: {str(e)}")
            session.rollback()
            return None
        finally:
            session.close()

    def get_user_analytics_summary(
        self,
        user_id: int,
        date_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict:
        """
        Get aggregated analytics for user in date range

        Args:
            user_id: User ID
            date_range: Optional tuple of (start_date, end_date)
                       Defaults to last 30 days if not provided

        Returns:
            Dict containing:
                - total_posts: Number of posts published
                - total_impressions: Sum of all impressions
                - total_engagements: Sum of all engagements
                - avg_engagement_rate: Average engagement rate
                - best_post: Dict with best performing post info
                - worst_post: Dict with worst performing post info
                - engagement_by_type: Dict of engagement by content type
                - time_range: Dict with start and end dates
        """
        session = self.db_manager.get_session()

        try:
            # Set default date range (last 30 days)
            if not date_range:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=30)
                date_range = (start_date, end_date)

            start_date, end_date = date_range

            # Get all published posts in date range
            posts = session.query(Post).filter(
                and_(
                    Post.user_id == user_id,
                    Post.status == PostStatus.PUBLISHED,
                    Post.published_time >= start_date,
                    Post.published_time <= end_date
                )
            ).all()

            if not posts:
                self.logger.info(f"No published posts found for user {user_id} in date range")
                return {
                    'total_posts': 0,
                    'total_impressions': 0,
                    'total_engagements': 0,
                    'avg_engagement_rate': 0.0,
                    'time_range': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat()
                    }
                }

            # Aggregate metrics
            total_posts = len(posts)
            total_impressions = 0
            total_engagements = 0
            engagement_rates = []
            engagement_by_type = defaultdict(lambda: {'posts': 0, 'engagements': 0, 'impressions': 0})

            post_scores = []  # (post, score) tuples

            for post in posts:
                # Get latest analytics for each post
                analytics = session.query(PostAnalytics).filter(
                    PostAnalytics.post_id == post.id
                ).order_by(PostAnalytics.snapshot_time.desc()).first()

                if analytics:
                    impressions = analytics.impressions or 0
                    engagements = (
                        (analytics.likes or 0) +
                        (analytics.retweets or 0) +
                        (analytics.comments or 0) +
                        (analytics.shares or 0)
                    )

                    total_impressions += impressions
                    total_engagements += engagements

                    if impressions > 0:
                        eng_rate = (engagements / impressions) * 100
                        engagement_rates.append(eng_rate)

                    # Track by content type
                    if post.content_type:
                        content_type = post.content_type.value
                        engagement_by_type[content_type]['posts'] += 1
                        engagement_by_type[content_type]['engagements'] += engagements
                        engagement_by_type[content_type]['impressions'] += impressions

                    # Track for best/worst
                    post_scores.append((post, analytics.weighted_engagement_score or 0))

            # Calculate averages
            avg_engagement_rate = mean(engagement_rates) if engagement_rates else 0.0

            # Find best and worst posts
            best_post_data = None
            worst_post_data = None

            if post_scores:
                post_scores.sort(key=lambda x: x[1], reverse=True)

                best_post, best_score = post_scores[0]
                best_analytics = session.query(PostAnalytics).filter(
                    PostAnalytics.post_id == best_post.id
                ).order_by(PostAnalytics.snapshot_time.desc()).first()

                if best_analytics:
                    best_post_data = {
                        'post_id': best_post.id,
                        'content': best_post.content[:100] + '...' if len(best_post.content) > 100 else best_post.content,
                        'impressions': best_analytics.impressions,
                        'engagements': (
                            (best_analytics.likes or 0) +
                            (best_analytics.retweets or 0) +
                            (best_analytics.comments or 0) +
                            (best_analytics.shares or 0)
                        ),
                        'engagement_rate': best_analytics.engagement_rate,
                        'score': best_score
                    }

                # Worst post (last in sorted list)
                worst_post, worst_score = post_scores[-1]
                worst_analytics = session.query(PostAnalytics).filter(
                    PostAnalytics.post_id == worst_post.id
                ).order_by(PostAnalytics.snapshot_time.desc()).first()

                if worst_analytics:
                    worst_post_data = {
                        'post_id': worst_post.id,
                        'content': worst_post.content[:100] + '...' if len(worst_post.content) > 100 else worst_post.content,
                        'impressions': worst_analytics.impressions,
                        'engagements': (
                            (worst_analytics.likes or 0) +
                            (worst_analytics.retweets or 0) +
                            (worst_analytics.comments or 0) +
                            (worst_analytics.shares or 0)
                        ),
                        'engagement_rate': worst_analytics.engagement_rate,
                        'score': worst_score
                    }

            # Calculate engagement rate by content type
            for content_type, data in engagement_by_type.items():
                if data['impressions'] > 0:
                    data['engagement_rate'] = (data['engagements'] / data['impressions']) * 100
                else:
                    data['engagement_rate'] = 0.0

            summary = {
                'total_posts': total_posts,
                'total_impressions': total_impressions,
                'total_engagements': total_engagements,
                'avg_engagement_rate': round(avg_engagement_rate, 2),
                'best_post': best_post_data,
                'worst_post': worst_post_data,
                'engagement_by_type': dict(engagement_by_type),
                'time_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            }

            self.logger.info(
                f"User {user_id} analytics: {total_posts} posts, "
                f"{total_engagements} engagements, {avg_engagement_rate:.2f}% avg rate"
            )

            return summary

        except Exception as e:
            self.logger.error(f"Error getting user analytics summary: {str(e)}")
            return {
                'error': str(e),
                'total_posts': 0,
                'total_impressions': 0,
                'total_engagements': 0,
                'avg_engagement_rate': 0.0
            }
        finally:
            session.close()

    def identify_best_posting_times(self, user_id: int) -> List[Dict]:
        """
        Analyze past posts to find optimal posting times

        Analyzes engagement patterns by day of week and hour of day
        to identify when posts perform best.

        Args:
            user_id: User ID

        Returns:
            List of dicts with best posting times:
                - day_of_week: 0-6 (Monday-Sunday)
                - day_name: String name of day
                - hour: 0-23 (UTC)
                - avg_engagement_rate: Average engagement rate
                - posts_count: Number of posts at this time
                - total_impressions: Total impressions
        """
        session = self.db_manager.get_session()

        try:
            # Get all published posts from last 90 days
            cutoff_date = datetime.utcnow() - timedelta(days=90)

            posts = session.query(Post).filter(
                and_(
                    Post.user_id == user_id,
                    Post.status == PostStatus.PUBLISHED,
                    Post.published_time >= cutoff_date
                )
            ).all()

            if not posts:
                self.logger.info(f"No published posts found for user {user_id}")
                return []

            # Group by day of week and hour
            time_slot_metrics = defaultdict(lambda: {
                'engagement_rates': [],
                'impressions': [],
                'engagements': [],
                'posts': []
            })

            for post in posts:
                if not post.published_time:
                    continue

                # Get analytics
                analytics = session.query(PostAnalytics).filter(
                    PostAnalytics.post_id == post.id
                ).order_by(PostAnalytics.snapshot_time.desc()).first()

                if not analytics or not analytics.impressions:
                    continue

                # Extract time components
                pub_time = post.published_time
                day_of_week = pub_time.weekday()  # 0=Monday, 6=Sunday
                hour = pub_time.hour

                time_slot = (day_of_week, hour)

                # Calculate metrics
                impressions = analytics.impressions or 0
                engagements = (
                    (analytics.likes or 0) +
                    (analytics.retweets or 0) +
                    (analytics.comments or 0) +
                    (analytics.shares or 0)
                )

                engagement_rate = 0.0
                if impressions > 0:
                    engagement_rate = (engagements / impressions) * 100

                # Store metrics
                time_slot_metrics[time_slot]['engagement_rates'].append(engagement_rate)
                time_slot_metrics[time_slot]['impressions'].append(impressions)
                time_slot_metrics[time_slot]['engagements'].append(engagements)
                time_slot_metrics[time_slot]['posts'].append(post.id)

            # Calculate averages for each time slot
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

            time_slot_results = []
            for (day_of_week, hour), metrics in time_slot_metrics.items():
                if len(metrics['posts']) >= 2:  # Require at least 2 posts for statistical relevance
                    avg_engagement_rate = mean(metrics['engagement_rates'])
                    total_impressions = sum(metrics['impressions'])
                    total_engagements = sum(metrics['engagements'])

                    time_slot_results.append({
                        'day_of_week': day_of_week,
                        'day_name': day_names[day_of_week],
                        'hour': hour,
                        'avg_engagement_rate': round(avg_engagement_rate, 2),
                        'posts_count': len(metrics['posts']),
                        'total_impressions': total_impressions,
                        'total_engagements': total_engagements
                    })

            # Sort by engagement rate
            time_slot_results.sort(key=lambda x: x['avg_engagement_rate'], reverse=True)

            # Return top 10 time slots
            top_times = time_slot_results[:10]

            self.logger.info(
                f"Identified {len(top_times)} optimal posting times for user {user_id}"
            )

            return top_times

        except Exception as e:
            self.logger.error(f"Error identifying best posting times: {str(e)}")
            return []
        finally:
            session.close()

    def track_recruiter_engagement(self, user_id: int) -> Dict:
        """
        Track metrics specific to recruiter engagement

        Note: Twitter API doesn't provide recruiter-specific data.
        This is a placeholder that could be extended with LinkedIn API
        or manual tracking.

        Args:
            user_id: User ID

        Returns:
            Dict with recruiter engagement metrics:
                - profile_views_7d: Profile views last 7 days
                - profile_views_30d: Profile views last 30 days
                - connection_requests: New connection requests
                - inmails_received: InMails received
                - recruiter_engagements: Engagements from recruiters
                - estimated_recruiter_reach: Estimated reach to recruiters
        """
        session = self.db_manager.get_session()

        try:
            # Get analytics snapshots from last 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)

            analytics_records = session.query(Analytics).filter(
                and_(
                    Analytics.user_id == user_id,
                    Analytics.snapshot_date >= cutoff_date
                )
            ).order_by(Analytics.snapshot_date.desc()).all()

            # Get latest record for current metrics
            latest = analytics_records[0] if analytics_records else None

            # Calculate 7-day metrics
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_analytics = [a for a in analytics_records if a.snapshot_date >= seven_days_ago]

            profile_views_7d = sum(a.profile_views or 0 for a in recent_analytics)
            profile_views_30d = sum(a.profile_views or 0 for a in analytics_records)

            recruiter_metrics = {
                'profile_views_7d': profile_views_7d,
                'profile_views_30d': profile_views_30d,
                'connection_requests': latest.connections_new if latest else 0,
                'inmails_received': latest.inmails_received if latest else 0,
                'recruiter_engagements': latest.recruiter_messages if latest else 0,
                'profile_saves': latest.profile_saves if latest else 0,
                'conversations_started': latest.conversations_started if latest else 0,
                'interviews_scheduled': latest.interviews_scheduled if latest else 0,
            }

            # Calculate trends
            if len(analytics_records) >= 2:
                current_views = analytics_records[0].profile_views or 0
                previous_views = analytics_records[-1].profile_views or 0

                if previous_views > 0:
                    view_change_pct = ((current_views - previous_views) / previous_views) * 100
                    recruiter_metrics['view_change_pct'] = round(view_change_pct, 2)

            # Estimate recruiter reach (rough heuristic)
            # Assume ~10% of profile views are from recruiters
            estimated_recruiter_reach = int(profile_views_30d * 0.1)
            recruiter_metrics['estimated_recruiter_reach'] = estimated_recruiter_reach

            self.logger.info(
                f"Recruiter engagement for user {user_id}: "
                f"{profile_views_30d} views, {estimated_recruiter_reach} estimated recruiter reach"
            )

            return recruiter_metrics

        except Exception as e:
            self.logger.error(f"Error tracking recruiter engagement: {str(e)}")
            return {
                'error': str(e),
                'profile_views_7d': 0,
                'profile_views_30d': 0
            }
        finally:
            session.close()

    def generate_weekly_report(self, user_id: int) -> Dict:
        """
        Generate comprehensive weekly analytics report

        Combines all analytics into a single comprehensive report
        for the past 7 days.

        Args:
            user_id: User ID

        Returns:
            Dict containing:
                - summary: High-level summary stats
                - top_posts: Top 5 performing posts
                - engagement_breakdown: Engagement by content type
                - best_times: Optimal posting times
                - recruiter_metrics: Recruiter engagement data
                - trends: Week-over-week trends
                - recommendations: Actionable recommendations
        """
        session = self.db_manager.get_session()

        try:
            # Define date ranges
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            prev_start_date = start_date - timedelta(days=7)

            # Get current week analytics
            current_week = self.get_user_analytics_summary(
                user_id,
                date_range=(start_date, end_date)
            )

            # Get previous week for comparison
            previous_week = self.get_user_analytics_summary(
                user_id,
                date_range=(prev_start_date, start_date)
            )

            # Calculate trends
            trends = {}
            if previous_week['total_posts'] > 0:
                trends['posts_change'] = current_week['total_posts'] - previous_week['total_posts']

                if previous_week['total_impressions'] > 0:
                    impressions_change_pct = (
                        (current_week['total_impressions'] - previous_week['total_impressions']) /
                        previous_week['total_impressions']
                    ) * 100
                    trends['impressions_change_pct'] = round(impressions_change_pct, 2)

                if previous_week['avg_engagement_rate'] > 0:
                    engagement_change_pct = (
                        (current_week['avg_engagement_rate'] - previous_week['avg_engagement_rate']) /
                        previous_week['avg_engagement_rate']
                    ) * 100
                    trends['engagement_change_pct'] = round(engagement_change_pct, 2)

            # Get top 5 posts this week
            posts = session.query(Post).filter(
                and_(
                    Post.user_id == user_id,
                    Post.status == PostStatus.PUBLISHED,
                    Post.published_time >= start_date,
                    Post.published_time <= end_date
                )
            ).all()

            top_posts = []
            for post in posts:
                analytics = session.query(PostAnalytics).filter(
                    PostAnalytics.post_id == post.id
                ).order_by(PostAnalytics.snapshot_time.desc()).first()

                if analytics:
                    top_posts.append({
                        'post_id': post.id,
                        'content': post.content[:100] + '...' if len(post.content) > 100 else post.content,
                        'content_type': post.content_type.value if post.content_type else 'unknown',
                        'impressions': analytics.impressions or 0,
                        'engagement_rate': analytics.engagement_rate or 0.0,
                        'weighted_score': analytics.weighted_engagement_score or 0.0,
                        'published_at': post.published_time.isoformat() if post.published_time else None
                    })

            top_posts.sort(key=lambda x: x['weighted_score'], reverse=True)
            top_posts = top_posts[:5]

            # Get best posting times
            best_times = self.identify_best_posting_times(user_id)[:5]

            # Get recruiter metrics
            recruiter_metrics = self.track_recruiter_engagement(user_id)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                current_week,
                best_times,
                recruiter_metrics
            )

            # Compile report
            report = {
                'report_period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'summary': {
                    'total_posts': current_week['total_posts'],
                    'total_impressions': current_week['total_impressions'],
                    'total_engagements': current_week['total_engagements'],
                    'avg_engagement_rate': current_week['avg_engagement_rate']
                },
                'top_posts': top_posts,
                'engagement_breakdown': current_week.get('engagement_by_type', {}),
                'best_times': best_times,
                'recruiter_metrics': recruiter_metrics,
                'trends': trends,
                'recommendations': recommendations,
                'generated_at': datetime.utcnow().isoformat()
            }

            self.logger.info(f"Generated weekly report for user {user_id}")

            return report

        except Exception as e:
            self.logger.error(f"Error generating weekly report: {str(e)}")
            return {
                'error': str(e),
                'summary': {},
                'generated_at': datetime.utcnow().isoformat()
            }
        finally:
            session.close()

    def _generate_recommendations(
        self,
        week_summary: Dict,
        best_times: List[Dict],
        recruiter_metrics: Dict
    ) -> List[str]:
        """
        Generate actionable recommendations based on analytics

        Args:
            week_summary: Weekly analytics summary
            best_times: Best posting times
            recruiter_metrics: Recruiter engagement metrics

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Posting frequency
        posts_count = week_summary.get('total_posts', 0)
        if posts_count < 3:
            recommendations.append(
                "Increase posting frequency to 3-5 times per week for better reach and engagement."
            )
        elif posts_count > 10:
            recommendations.append(
                "Consider reducing posting frequency to focus on quality over quantity."
            )

        # Engagement rate
        engagement_rate = week_summary.get('avg_engagement_rate', 0.0)
        if engagement_rate < 2.0:
            recommendations.append(
                "Engagement rate is below average. Try more engaging formats like questions, polls, or controversial takes."
            )
        elif engagement_rate > 5.0:
            recommendations.append(
                "Excellent engagement rate! Keep up the current content strategy."
            )

        # Content type diversity
        engagement_by_type = week_summary.get('engagement_by_type', {})
        if len(engagement_by_type) < 3:
            recommendations.append(
                "Diversify content types to reach different audience segments."
            )

        # Best posting times
        if best_times:
            top_time = best_times[0]
            recommendations.append(
                f"Post more on {top_time['day_name']}s at {top_time['hour']}:00 UTC "
                f"(avg {top_time['avg_engagement_rate']:.1f}% engagement rate)."
            )

        # Recruiter engagement
        profile_views = recruiter_metrics.get('profile_views_7d', 0)
        if profile_views < 50:
            recommendations.append(
                "Low profile views. Consider adding more professional insights and industry commentary."
            )

        return recommendations

    def create_user_analytics_snapshot(self, user_id: int, platform: Platform) -> Optional[Analytics]:
        """
        Create a new analytics snapshot for user-level metrics

        Args:
            user_id: User ID
            platform: Platform (Twitter/LinkedIn)

        Returns:
            Analytics object if successful, None otherwise
        """
        session = self.db_manager.get_session()

        try:
            # Get user metrics from Twitter API
            user_metrics = {}
            if self.twitter_handler:
                try:
                    user_metrics = self.twitter_handler.get_user_metrics()
                except Exception as e:
                    self.logger.warning(f"Failed to fetch user metrics: {str(e)}")

            # Get posts published this week
            week_ago = datetime.utcnow() - timedelta(days=7)
            posts_this_week = session.query(Post).filter(
                and_(
                    Post.user_id == user_id,
                    Post.status == PostStatus.PUBLISHED,
                    Post.published_time >= week_ago
                )
            ).count()

            # Calculate average engagement rate
            week_summary = self.get_user_analytics_summary(
                user_id,
                date_range=(week_ago, datetime.utcnow())
            )

            # Create analytics snapshot
            analytics = Analytics(
                user_id=user_id,
                platform=platform,
                snapshot_date=datetime.utcnow(),
                profile_views=user_metrics.get('profile_views', 0),
                connections_new=0,  # Not available from Twitter
                search_appearances=0,  # Not available from Twitter
                posts_published_week=posts_this_week,
                avg_engagement_rate=week_summary.get('avg_engagement_rate', 0.0)
            )

            session.add(analytics)
            session.commit()
            session.refresh(analytics)

            self.logger.info(f"Created analytics snapshot for user {user_id}")

            return analytics

        except Exception as e:
            self.logger.error(f"Error creating user analytics snapshot: {str(e)}")
            session.rollback()
            return None
        finally:
            session.close()
