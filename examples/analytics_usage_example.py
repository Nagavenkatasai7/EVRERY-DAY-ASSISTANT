"""
Social Media Analytics Usage Example

Demonstrates how to use the AnalyticsCollector for comprehensive
social media performance tracking and reporting.

Usage:
    python examples/analytics_usage_example.py
"""

import os
from datetime import datetime, timedelta
from src.social_media.models import DatabaseManager, User, Post, PostStatus, Platform, ContentType
from src.social_media.analytics import AnalyticsCollector
from src.social_media.twitter_handler import TwitterHandler


def example_basic_analytics():
    """Example: Basic analytics collection"""
    print("=== Basic Analytics Collection ===\n")

    # Initialize database and analytics collector
    db_manager = DatabaseManager("sqlite:///example_analytics.db")
    db_manager.create_tables()

    # Initialize with Twitter handler (requires credentials)
    # For this example, we'll use None and demonstrate the structure
    collector = AnalyticsCollector(db_manager, twitter_handler=None)

    # Create sample user
    session = db_manager.get_session()
    user = User(
        username="ai_researcher",
        email="researcher@example.com",
        full_name="AI Researcher",
        research_area="Multi-agent AI Systems"
    )
    session.add(user)
    session.commit()

    print(f"Created user: {user.username}")
    print()

    session.close()


def example_post_metrics():
    """Example: Collect metrics for a specific post"""
    print("=== Post Metrics Collection ===\n")

    db_manager = DatabaseManager("sqlite:///example_analytics.db")

    # In production, initialize with real Twitter handler
    # twitter_handler = TwitterHandler(
    #     api_key=os.getenv("TWITTER_API_KEY"),
    #     api_secret=os.getenv("TWITTER_API_SECRET"),
    #     access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
    #     access_secret=os.getenv("TWITTER_ACCESS_SECRET")
    # )

    collector = AnalyticsCollector(db_manager, twitter_handler=None)

    # Example: Collect metrics for post ID 123
    post_id = 123
    result = collector.collect_post_metrics(post_id)

    if result['success']:
        metrics = result['metrics']
        print(f"Post {post_id} Metrics:")
        print(f"  Impressions: {metrics['impressions']:,}")
        print(f"  Likes: {metrics['likes']:,}")
        print(f"  Retweets: {metrics['retweets']:,}")
        print(f"  Replies: {metrics['replies']:,}")
        print(f"  Quotes: {metrics['quotes']:,}")
    else:
        print(f"Failed to collect metrics: {result['error']}")

    print()


def example_engagement_rate():
    """Example: Calculate engagement rate"""
    print("=== Engagement Rate Calculation ===\n")

    db_manager = DatabaseManager("sqlite:///example_analytics.db")
    collector = AnalyticsCollector(db_manager)

    post_id = 123
    rate = collector.calculate_engagement_rate(post_id)

    print(f"Post {post_id} Engagement Rate: {rate:.2f}%")
    print()


def example_user_summary():
    """Example: Get user analytics summary"""
    print("=== User Analytics Summary ===\n")

    db_manager = DatabaseManager("sqlite:///example_analytics.db")
    collector = AnalyticsCollector(db_manager)

    user_id = 1

    # Get summary for last 30 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    summary = collector.get_user_analytics_summary(
        user_id=user_id,
        date_range=(start_date, end_date)
    )

    print(f"User {user_id} - Last 30 Days Summary:")
    print(f"  Total Posts: {summary['total_posts']}")
    print(f"  Total Impressions: {summary['total_impressions']:,}")
    print(f"  Total Engagements: {summary['total_engagements']:,}")
    print(f"  Avg Engagement Rate: {summary['avg_engagement_rate']:.2f}%")
    print()

    if summary.get('best_post'):
        print("Best Performing Post:")
        print(f"  Content: {summary['best_post']['content'][:60]}...")
        print(f"  Engagement Rate: {summary['best_post']['engagement_rate']:.2f}%")
        print()

    if summary.get('engagement_by_type'):
        print("Performance by Content Type:")
        for content_type, data in summary['engagement_by_type'].items():
            print(f"  {content_type}:")
            print(f"    Posts: {data['posts']}")
            print(f"    Avg Engagement: {data.get('engagement_rate', 0):.2f}%")
        print()


def example_best_posting_times():
    """Example: Identify optimal posting times"""
    print("=== Best Posting Times Analysis ===\n")

    db_manager = DatabaseManager("sqlite:///example_analytics.db")
    collector = AnalyticsCollector(db_manager)

    user_id = 1
    best_times = collector.identify_best_posting_times(user_id)

    print(f"Top {min(5, len(best_times))} Posting Times for User {user_id}:")
    for i, time_slot in enumerate(best_times[:5], 1):
        print(f"\n{i}. {time_slot['day_name']} at {time_slot['hour']:02d}:00 UTC")
        print(f"   Avg Engagement Rate: {time_slot['avg_engagement_rate']:.2f}%")
        print(f"   Posts Analyzed: {time_slot['posts_count']}")
        print(f"   Total Impressions: {time_slot['total_impressions']:,}")
    print()


def example_recruiter_tracking():
    """Example: Track recruiter engagement"""
    print("=== Recruiter Engagement Tracking ===\n")

    db_manager = DatabaseManager("sqlite:///example_analytics.db")
    collector = AnalyticsCollector(db_manager)

    user_id = 1
    metrics = collector.track_recruiter_engagement(user_id)

    print(f"Recruiter Engagement Metrics for User {user_id}:")
    print(f"  Profile Views (7 days): {metrics['profile_views_7d']:,}")
    print(f"  Profile Views (30 days): {metrics['profile_views_30d']:,}")
    print(f"  Connection Requests: {metrics['connection_requests']}")
    print(f"  InMails Received: {metrics['inmails_received']}")
    print(f"  Recruiter Engagements: {metrics['recruiter_engagements']}")
    print(f"  Estimated Recruiter Reach: {metrics['estimated_recruiter_reach']}")

    if 'view_change_pct' in metrics:
        print(f"  View Change: {metrics['view_change_pct']:+.1f}%")
    print()


def example_weekly_report():
    """Example: Generate comprehensive weekly report"""
    print("=== Weekly Performance Report ===\n")

    db_manager = DatabaseManager("sqlite:///example_analytics.db")
    collector = AnalyticsCollector(db_manager)

    user_id = 1
    report = collector.generate_weekly_report(user_id)

    # Summary Section
    print("WEEKLY SUMMARY")
    print("=" * 50)
    print(f"Posts Published: {report['summary']['total_posts']}")
    print(f"Total Impressions: {report['summary']['total_impressions']:,}")
    print(f"Total Engagements: {report['summary']['total_engagements']:,}")
    print(f"Avg Engagement Rate: {report['summary']['avg_engagement_rate']:.2f}%")
    print()

    # Top Posts
    if report['top_posts']:
        print("TOP PERFORMING POSTS")
        print("=" * 50)
        for i, post in enumerate(report['top_posts'][:3], 1):
            print(f"\n{i}. {post['content'][:70]}...")
            print(f"   Type: {post['content_type']}")
            print(f"   Impressions: {post['impressions']:,}")
            print(f"   Engagement Rate: {post['engagement_rate']:.2f}%")
        print()

    # Trends
    if report['trends']:
        print("TRENDS")
        print("=" * 50)
        for key, value in report['trends'].items():
            if isinstance(value, float):
                print(f"{key}: {value:+.1f}%")
            else:
                print(f"{key}: {value}")
        print()

    # Best Times
    if report['best_times']:
        print("OPTIMAL POSTING TIMES")
        print("=" * 50)
        for time_slot in report['best_times'][:3]:
            print(f"• {time_slot['day_name']} at {time_slot['hour']:02d}:00 UTC")
            print(f"  ({time_slot['avg_engagement_rate']:.1f}% avg engagement)")
        print()

    # Recruiter Metrics
    print("RECRUITER ENGAGEMENT")
    print("=" * 50)
    rm = report['recruiter_metrics']
    print(f"Profile Views (7d): {rm['profile_views_7d']:,}")
    print(f"Connection Requests: {rm['connection_requests']}")
    print(f"InMails Received: {rm['inmails_received']}")
    print()

    # Recommendations
    if report['recommendations']:
        print("RECOMMENDATIONS")
        print("=" * 50)
        for rec in report['recommendations']:
            print(f"• {rec}")
        print()

    print(f"Report generated at: {report['generated_at']}")
    print()


def example_scheduled_collection():
    """Example: Set up scheduled analytics collection"""
    print("=== Scheduled Analytics Collection ===\n")

    from apscheduler.schedulers.background import BackgroundScheduler

    db_manager = DatabaseManager("sqlite:///example_analytics.db")
    collector = AnalyticsCollector(db_manager)

    def collect_recent_analytics():
        """Collect analytics for posts from last 24 hours"""
        session = db_manager.get_session()

        recent_posts = session.query(Post).filter(
            Post.status == PostStatus.PUBLISHED,
            Post.published_time >= datetime.utcnow() - timedelta(days=1)
        ).all()

        print(f"[{datetime.now()}] Collecting analytics for {len(recent_posts)} posts")

        for post in recent_posts:
            result = collector.update_post_analytics(post.id)
            if result:
                print(f"  Updated analytics for post {post.id}")

        session.close()

    # Create scheduler
    scheduler = BackgroundScheduler()

    # Schedule analytics collection every hour
    scheduler.add_job(
        collect_recent_analytics,
        'interval',
        hours=1,
        id='hourly_analytics'
    )

    # Schedule weekly reports every Monday at 9 AM
    scheduler.add_job(
        lambda: example_weekly_report(),
        'cron',
        day_of_week='mon',
        hour=9,
        minute=0,
        id='weekly_report'
    )

    print("Scheduled Jobs:")
    print("  1. Analytics Collection: Every hour")
    print("  2. Weekly Report: Every Monday at 9:00 AM")
    print()
    print("(Scheduler not started in example)")
    # scheduler.start()  # Uncomment to actually start


def example_error_handling():
    """Example: Proper error handling"""
    print("=== Error Handling Examples ===\n")

    db_manager = DatabaseManager("sqlite:///example_analytics.db")
    collector = AnalyticsCollector(db_manager)

    # Example 1: Handle failed metrics collection
    print("1. Handling failed metrics collection:")
    result = collector.collect_post_metrics(post_id=99999)
    if not result['success']:
        print(f"   Error: {result['error']}")
        print(f"   Action: Log error and retry later")
    print()

    # Example 2: Handle missing analytics data
    print("2. Handling missing analytics:")
    rate = collector.calculate_engagement_rate(post_id=99999)
    print(f"   Engagement Rate: {rate:.2f}%")
    print(f"   Returns 0.0 safely when no data exists")
    print()

    # Example 3: Handle empty summaries
    print("3. Handling empty user summary:")
    summary = collector.get_user_analytics_summary(user_id=99999)
    print(f"   Total Posts: {summary['total_posts']}")
    print(f"   Returns safe defaults for missing data")
    print()


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("SOCIAL MEDIA ANALYTICS - USAGE EXAMPLES")
    print("=" * 60 + "\n")

    try:
        example_basic_analytics()
        example_post_metrics()
        example_engagement_rate()
        example_user_summary()
        example_best_posting_times()
        example_recruiter_tracking()
        example_weekly_report()
        example_scheduled_collection()
        example_error_handling()

        print("\n" + "=" * 60)
        print("Examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nError running examples: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
