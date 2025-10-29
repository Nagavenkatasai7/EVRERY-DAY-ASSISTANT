# Social Media Analytics Collection System

## Overview

A comprehensive analytics collection and reporting system for the social media automation platform. Collects metrics from Twitter API, calculates derived metrics, and generates actionable insights.

## Features

### 1. Post-Level Analytics
- **Real-time Metrics Collection**: Fetch engagement data from Twitter API
- **Engagement Tracking**: Likes, retweets, replies, quotes, impressions
- **Derived Metrics**:
  - Engagement rate: `(likes + retweets + replies + quotes) / impressions * 100`
  - Weighted engagement score: `likes*1 + retweets*2 + replies*3 + quotes*2`
- **Time-series Tracking**: Multiple snapshots over time to track growth

### 2. User-Level Analytics
- **Aggregated Performance**: Summary stats across all posts
- **Content Type Analysis**: Performance breakdown by content type
- **Best/Worst Posts**: Identify top and bottom performers
- **Date Range Support**: Custom date ranges for flexible reporting

### 3. Posting Time Optimization
- **Pattern Analysis**: Identify optimal posting times by day/hour
- **Statistical Relevance**: Requires minimum 2 posts per time slot
- **Historical Data**: Analyzes last 90 days of posting history
- **Top 10 Time Slots**: Returns best performing times ranked by engagement

### 4. Recruiter Engagement Tracking
- **Profile Views**: 7-day and 30-day tracking
- **Connection Metrics**: New connections, InMails received
- **Trend Analysis**: Week-over-week growth calculations
- **Estimated Reach**: Heuristic-based recruiter reach estimation

### 5. Weekly Performance Reports
- **Comprehensive Summary**: All key metrics in one place
- **Top Posts**: Best 5 performing posts of the week
- **Trend Analysis**: Week-over-week comparisons
- **Actionable Recommendations**: Data-driven suggestions
- **Engagement Breakdown**: Performance by content type

## Installation

The analytics system is integrated into the social media automation platform:

```python
from src.social_media.analytics import AnalyticsCollector
from src.social_media.models import DatabaseManager
from src.social_media.twitter_handler import TwitterHandler

# Initialize
db_manager = DatabaseManager()
twitter_handler = TwitterHandler(
    api_key="your_key",
    api_secret="your_secret",
    access_token="your_token",
    access_secret="your_secret"
)
collector = AnalyticsCollector(db_manager, twitter_handler)
```

## Usage Examples

### Collect Post Metrics

```python
# Collect metrics for a specific post
result = collector.collect_post_metrics(post_id=123)

if result['success']:
    metrics = result['metrics']
    print(f"Impressions: {metrics['impressions']}")
    print(f"Likes: {metrics['likes']}")
    print(f"Retweets: {metrics['retweets']}")
```

### Update Post Analytics

```python
# Fetch latest metrics and update database
analytics = collector.update_post_analytics(post_id=123)

if analytics:
    print(f"Engagement Rate: {analytics.engagement_rate:.2f}%")
    print(f"Weighted Score: {analytics.weighted_engagement_score}")
```

### Calculate Engagement Rate

```python
# Calculate engagement rate for a post
rate = collector.calculate_engagement_rate(post_id=123)
print(f"Engagement Rate: {rate:.2f}%")
```

### Get User Analytics Summary

```python
# Get summary for last 30 days
from datetime import datetime, timedelta

end_date = datetime.utcnow()
start_date = end_date - timedelta(days=30)

summary = collector.get_user_analytics_summary(
    user_id=1,
    date_range=(start_date, end_date)
)

print(f"Total Posts: {summary['total_posts']}")
print(f"Total Impressions: {summary['total_impressions']}")
print(f"Avg Engagement Rate: {summary['avg_engagement_rate']:.2f}%")

# Best performing post
if summary['best_post']:
    print(f"Top Post: {summary['best_post']['content']}")
    print(f"Engagement Rate: {summary['best_post']['engagement_rate']:.2f}%")
```

### Identify Best Posting Times

```python
# Analyze optimal posting times
best_times = collector.identify_best_posting_times(user_id=1)

for time_slot in best_times[:5]:
    print(f"{time_slot['day_name']} at {time_slot['hour']:02d}:00 UTC")
    print(f"  Avg Engagement: {time_slot['avg_engagement_rate']:.2f}%")
    print(f"  Posts: {time_slot['posts_count']}")
    print()
```

### Track Recruiter Engagement

```python
# Get recruiter-specific metrics
recruiter_metrics = collector.track_recruiter_engagement(user_id=1)

print(f"Profile Views (7d): {recruiter_metrics['profile_views_7d']}")
print(f"Profile Views (30d): {recruiter_metrics['profile_views_30d']}")
print(f"Connection Requests: {recruiter_metrics['connection_requests']}")
print(f"InMails Received: {recruiter_metrics['inmails_received']}")
print(f"Estimated Recruiter Reach: {recruiter_metrics['estimated_recruiter_reach']}")
```

### Generate Weekly Report

```python
# Generate comprehensive weekly report
report = collector.generate_weekly_report(user_id=1)

# Summary
print("=== Weekly Summary ===")
print(f"Posts: {report['summary']['total_posts']}")
print(f"Impressions: {report['summary']['total_impressions']}")
print(f"Engagements: {report['summary']['total_engagements']}")
print(f"Avg Engagement Rate: {report['summary']['avg_engagement_rate']:.2f}%")

# Top posts
print("\n=== Top Posts ===")
for post in report['top_posts'][:3]:
    print(f"- {post['content'][:50]}...")
    print(f"  Engagement Rate: {post['engagement_rate']:.2f}%")

# Trends
print("\n=== Trends ===")
for key, value in report['trends'].items():
    print(f"{key}: {value}")

# Recommendations
print("\n=== Recommendations ===")
for rec in report['recommendations']:
    print(f"- {rec}")
```

## API Reference

### AnalyticsCollector

#### `__init__(db_manager, twitter_handler=None)`
Initialize the analytics collector.

**Parameters:**
- `db_manager` (DatabaseManager): Database manager instance
- `twitter_handler` (TwitterHandler, optional): Twitter API handler

#### `collect_post_metrics(post_id: int) -> Dict`
Collect metrics for a specific post from Twitter API.

**Returns:**
```python
{
    'success': bool,
    'metrics': {
        'impressions': int,
        'likes': int,
        'retweets': int,
        'replies': int,
        'quotes': int,
        'url_clicks': int,
        'profile_clicks': int,
        'media_views': int
    },
    'collected_at': datetime,
    'error': str  # Only if success is False
}
```

#### `calculate_engagement_rate(post_id: int) -> float`
Calculate engagement rate for a post.

**Returns:** Engagement rate as percentage (0.0 - 100.0)

#### `update_post_analytics(post_id: int) -> Optional[PostAnalytics]`
Fetch latest metrics and update PostAnalytics table.

**Returns:** PostAnalytics object if successful, None otherwise

#### `get_user_analytics_summary(user_id: int, date_range: tuple) -> Dict`
Get aggregated analytics for user in date range.

**Parameters:**
- `user_id` (int): User ID
- `date_range` (tuple, optional): (start_date, end_date) tuple

**Returns:**
```python
{
    'total_posts': int,
    'total_impressions': int,
    'total_engagements': int,
    'avg_engagement_rate': float,
    'best_post': {...},
    'worst_post': {...},
    'engagement_by_type': {...},
    'time_range': {...}
}
```

#### `identify_best_posting_times(user_id: int) -> List[Dict]`
Analyze past posts to find optimal posting times.

**Returns:**
```python
[
    {
        'day_of_week': int,  # 0-6 (Monday-Sunday)
        'day_name': str,
        'hour': int,  # 0-23 (UTC)
        'avg_engagement_rate': float,
        'posts_count': int,
        'total_impressions': int,
        'total_engagements': int
    },
    ...
]
```

#### `track_recruiter_engagement(user_id: int) -> Dict`
Track metrics specific to recruiter engagement.

**Returns:**
```python
{
    'profile_views_7d': int,
    'profile_views_30d': int,
    'connection_requests': int,
    'inmails_received': int,
    'recruiter_engagements': int,
    'profile_saves': int,
    'conversations_started': int,
    'interviews_scheduled': int,
    'estimated_recruiter_reach': int,
    'view_change_pct': float  # If available
}
```

#### `generate_weekly_report(user_id: int) -> Dict`
Generate comprehensive weekly analytics report.

**Returns:**
```python
{
    'report_period': {...},
    'summary': {...},
    'top_posts': [...],
    'engagement_breakdown': {...},
    'best_times': [...],
    'recruiter_metrics': {...},
    'trends': {...},
    'recommendations': [...],
    'generated_at': str
}
```

## Database Schema

### PostAnalytics Table
Stores detailed analytics for each post:
- `post_id`: Foreign key to Post
- `impressions`, `views`, `likes`, `comments`, `shares`, `retweets`, `clicks`
- `engagement_rate`: Calculated percentage
- `weighted_engagement_score`: Custom weighted score
- `snapshot_time`: When metrics were collected
- `hours_since_published`: Time elapsed since posting

### Analytics Table
Stores user-level analytics snapshots:
- `user_id`: Foreign key to User
- `platform`: Twitter/LinkedIn
- `snapshot_date`: Date of snapshot
- `profile_views`, `connections_new`, `search_appearances`
- `inmails_received`, `recruiter_messages`, `profile_saves`
- `posts_published_week`, `avg_engagement_rate`
- `interviews_scheduled`, `profile_to_interview_rate`

## Error Handling

The system implements comprehensive error handling:

### Rate Limiting
```python
try:
    result = collector.collect_post_metrics(post_id)
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
    # Wait and retry
```

### API Errors
```python
result = collector.collect_post_metrics(post_id)
if not result['success']:
    print(f"Error: {result['error']}")
    # Handle error
```

### Missing Data
All methods return safe defaults when data is unavailable:
- `calculate_engagement_rate()` returns `0.0`
- `get_user_analytics_summary()` returns empty structure
- `identify_best_posting_times()` returns empty list

## Performance Considerations

### Caching Strategy
- Analytics snapshots are stored in database
- Avoids repeated API calls for same data
- Time-series tracking with `snapshot_time`

### Rate Limit Compliance
- All API calls use exponential backoff retry logic
- Respects Twitter API rate limits
- Logs all rate limit events

### Query Optimization
- Uses indexed columns for date range queries
- Batch processing for multiple posts
- Efficient aggregation with SQLAlchemy

## Testing

Comprehensive test suite with 30+ tests covering:
- Metrics collection (success/failure cases)
- Engagement rate calculations
- User analytics aggregation
- Best posting times analysis
- Recruiter engagement tracking
- Weekly report generation
- Edge cases and error handling

Run tests:
```bash
pytest tests/social_media/test_analytics.py -v
```

Test coverage: **83%** of analytics.py code

## Metrics Calculation Details

### Engagement Rate
```
engagement_rate = (likes + retweets + replies + quotes) / impressions * 100
```

### Weighted Engagement Score
```
score = (likes * 1.0) + (retweets * 2.0) + (replies * 3.0) + (quotes * 2.0)
```

Weights reflect relative value:
- **Replies (3x)**: Highest engagement, indicates meaningful interaction
- **Retweets & Quotes (2x)**: Strong signal, amplifies reach
- **Likes (1x)**: Baseline engagement

### Recruiter Reach Estimation
```
estimated_recruiter_reach = profile_views_30d * 0.10
```

Assumes ~10% of profile views are from recruiters (industry heuristic).

## Integration Examples

### Scheduled Analytics Collection
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def collect_analytics_for_recent_posts():
    """Collect analytics for posts published in last 24 hours"""
    session = db_manager.get_session()

    recent_posts = session.query(Post).filter(
        Post.status == PostStatus.PUBLISHED,
        Post.published_time >= datetime.utcnow() - timedelta(days=1)
    ).all()

    for post in recent_posts:
        collector.update_post_analytics(post.id)

    session.close()

# Schedule to run every hour
scheduler.add_job(
    collect_analytics_for_recent_posts,
    'interval',
    hours=1,
    id='analytics_collection'
)

scheduler.start()
```

### Weekly Report Email
```python
def send_weekly_analytics_email(user_id: int):
    """Generate and send weekly analytics report"""
    report = collector.generate_weekly_report(user_id)

    email_body = f"""
    Weekly Social Media Report

    Posts Published: {report['summary']['total_posts']}
    Total Impressions: {report['summary']['total_impressions']:,}
    Average Engagement: {report['summary']['avg_engagement_rate']:.2f}%

    Top Performing Post:
    {report['top_posts'][0]['content']}
    Engagement Rate: {report['top_posts'][0]['engagement_rate']:.2f}%

    Recommendations:
    {chr(10).join('- ' + r for r in report['recommendations'])}
    """

    # Send email (implementation depends on email service)
    send_email(
        to=user.email,
        subject="Your Weekly Social Media Analytics",
        body=email_body
    )
```

## Recommendations Algorithm

The system generates actionable recommendations based on:

1. **Posting Frequency**
   - < 3 posts/week: Suggest increasing to 3-5
   - > 10 posts/week: Suggest reducing for quality

2. **Engagement Rate**
   - < 2%: Suggest more engaging content formats
   - > 5%: Praise and encourage continuing strategy

3. **Content Diversity**
   - < 3 content types: Suggest diversifying

4. **Posting Times**
   - Recommends top time slot with actual stats

5. **Profile Views**
   - < 50/week: Suggest more professional content

## Troubleshooting

### No Metrics Collected
- Verify `external_post_id` is set on Post
- Check Twitter handler is configured
- Ensure post status is `PUBLISHED`

### Zero Engagement Rate
- Check if post has impressions > 0
- Verify analytics snapshot exists
- Confirm metrics were successfully collected

### Empty Best Times Analysis
- Requires at least 2 posts per time slot
- Check date range (analyzes last 90 days)
- Ensure posts have analytics data

## Limitations

1. **Twitter API Access**: Requires Twitter API credentials
2. **Public Metrics Only**: Advanced metrics require Twitter Analytics API
3. **Recruiter Data**: LinkedIn provides better recruiter-specific data
4. **Historical Data**: Limited by when you started collecting analytics

## Future Enhancements

- [ ] LinkedIn API integration for recruiter metrics
- [ ] Machine learning for engagement prediction
- [ ] A/B testing framework integration
- [ ] Real-time dashboard with WebSocket updates
- [ ] Sentiment analysis on replies
- [ ] Competitor benchmarking
- [ ] Automated content recommendations
- [ ] Export reports to PDF/CSV

## Support

For issues or questions:
- Check test suite for usage examples
- Review code comments in `analytics.py`
- Consult `SOCIAL_MEDIA_GUIDE.md` for platform guidelines

## License

Part of the Research Assistant social media automation platform.
