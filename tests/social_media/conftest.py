"""
Social Media Automation Test Fixtures

References:
- pytest fixtures: https://docs.pytest.org/en/stable/fixture.html
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- Testing best practices: SOCIAL_MEDIA_GUIDE.md
"""

import pytest
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from cryptography.fernet import Fernet


# Import social media components
from src.social_media.models import (
    Base, User, Post, PostStatus, Platform, ContentType,
    OAuthToken, DatabaseManager, TokenEncryption,
    PostAnalytics, Analytics, TrendingTopic
)


@pytest.fixture(scope="session", autouse=True)
def sm_encryption_key():
    """Generate encryption key for social media tests - runs automatically"""
    key = Fernet.generate_key().decode()
    os.environ['ENCRYPTION_KEY'] = key

    # Reinitialize the global token_encryptor with the test key
    import src.social_media.models as models_module
    models_module.token_encryptor = TokenEncryption()

    return key


@pytest.fixture
def sm_temp_db():
    """Temporary database for social media tests"""
    db_fd, db_path = tempfile.mkstemp(suffix='_sm_test.db')
    db_url = f'sqlite:///{db_path}'

    yield db_url

    os.close(db_fd)
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def sm_db_manager(sm_temp_db):
    """Database manager for social media"""
    manager = DatabaseManager(database_url=sm_temp_db)
    manager.create_tables()
    yield manager
    # Close any open sessions and dispose engine
    try:
        # Dispose of the engine to close all connections
        manager.engine.dispose()
    except Exception:
        pass


@pytest.fixture
def sm_session(sm_db_manager):
    """Database session"""
    session = sm_db_manager.get_session()
    yield session
    # Rollback any pending transactions
    try:
        session.rollback()
    except Exception:
        pass
    # Close the session
    try:
        session.close()
    except Exception:
        pass


@pytest.fixture
def test_sm_user(sm_session):
    """Test user for social media"""
    user = User(
        username="phd_researcher",
        email="researcher@university.edu",
        full_name="Dr. AI Researcher",
        research_area="Multi-agent AI and RAG systems",
        current_projects=["Research Assistant", "Multi-agent Orchestration", "RAG Chatbot"],
        unique_perspective="Bridging research and production with AI tools"
    )
    sm_session.add(user)
    sm_session.commit()
    sm_session.refresh(user)
    return user


@pytest.fixture
def test_twitter_token(sm_session, test_sm_user, sm_encryption_key):
    """OAuth token for Twitter"""
    encryptor = TokenEncryption()

    token = OAuthToken(
        user_id=test_sm_user.id,
        platform=Platform.TWITTER,
        access_token_encrypted=encryptor.encrypt("test_twitter_access"),
        token_secret_encrypted=encryptor.encrypt("test_twitter_secret")
    )
    sm_session.add(token)
    sm_session.commit()
    sm_session.refresh(token)
    return token


@pytest.fixture
def draft_post(sm_session, test_sm_user):
    """Draft post for testing"""
    post = Post(
        user_id=test_sm_user.id,
        platform=Platform.TWITTER,
        content="Just implemented RAG with prompt caching - 80% cost reduction! #AI #RAG",
        content_type=ContentType.PROJECT_SHOWCASE,
        status=PostStatus.DRAFT,
        ai_generated=True,
        ai_temperature=0.75
    )
    sm_session.add(post)
    sm_session.commit()
    sm_session.refresh(post)
    return post


@pytest.fixture
def scheduled_post(sm_session, test_sm_user):
    """Scheduled post"""
    post = Post(
        user_id=test_sm_user.id,
        platform=Platform.TWITTER,
        content="Exploring multi-agent coordination patterns. Fascinating how LLMs handle task decomposition.",
        content_type=ContentType.LEARNING_UPDATE,
        status=PostStatus.SCHEDULED,
        scheduled_time=datetime.utcnow() + timedelta(hours=2),
        ai_generated=True
    )
    sm_session.add(post)
    sm_session.commit()
    sm_session.refresh(post)
    return post


@pytest.fixture
def mock_tweepy():
    """Mock Tweepy client"""
    with patch('tweepy.Client') as mock_client:
        # Mock create_tweet
        mock_response = MagicMock()
        mock_response.data = {'id': '1234567890123456789', 'text': 'Test tweet'}
        mock_client.return_value.create_tweet.return_value = mock_response

        # Mock get_me
        mock_user = MagicMock()
        mock_user.data = {'id': '123456', 'username': 'test_user', 'name': 'Test User'}
        mock_client.return_value.get_me.return_value = mock_user

        # Mock get_tweet
        mock_tweet = MagicMock()
        mock_tweet_data = MagicMock()
        mock_tweet_data.id = '1234567890123456789'
        mock_tweet_data.text = 'Test tweet'
        mock_tweet_data.public_metrics = {
            'impression_count': 1500,
            'like_count': 45,
            'retweet_count': 12,
            'reply_count': 5
        }
        mock_tweet_data.created_at = '2025-01-15T10:00:00Z'
        mock_tweet.data = mock_tweet_data
        mock_client.return_value.get_tweet.return_value = mock_tweet

        yield mock_client


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic Claude client"""
    with patch('anthropic.Anthropic') as mock_client:
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="Here's a tweet about your project:\n\nJust shipped a RAG system with 80% cost savings using prompt caching. Game changer for production AI.")
        ]
        mock_client.return_value.messages.create.return_value = mock_response
        yield mock_client


@pytest.fixture
def mock_tavily():
    """Mock Tavily client"""
    with patch('src.social_media.trend_discovery.TavilyClient') as mock_client:
        mock_client.return_value.search.return_value = {
            'results': [
                {
                    'title': 'New RAG Techniques Revolutionize AI Systems',
                    'url': 'https://example.com/rag-2025',
                    'content': 'Advanced retrieval patterns improve accuracy by 40%...',
                    'score': 0.95,
                    'published_date': '2025-01-15'
                },
                {
                    'title': 'Multi-Agent AI: Coordination Strategies',
                    'url': 'https://example.com/multi-agent',
                    'content': 'Best practices for orchestrating multiple AI agents...',
                    'score': 0.92,
                    'published_date': '2025-01-14'
                }
            ]
        }
        yield mock_client


@pytest.fixture
def sample_project_showcase_params():
    """Parameters for project showcase generation"""
    return {
        'project_name': 'Multi-Agent Research Assistant',
        'project_description': 'AI research assistant with RAG, multi-agent orchestration, and Claude 4',
        'technical_details': 'Python, LangChain, FAISS, APScheduler, Streamlit, Claude API',
        'results_metrics': '98% cost savings with Grok, 80% faster research, 141/141 tests passing',
        'platform': Platform.TWITTER
    }


@pytest.fixture
def ai_red_flag_content():
    """Content with AI detection red flags"""
    return """I'm excited to announce my new AI project! 🚀✨⭐💡

I'm thrilled to share these amazing features:
• Advanced machine learning capabilities
• Cutting-edge natural language processing
• Revolutionary AI algorithms
• Game-changing performance improvements

I'm delighted to present this innovative solution!"""


@pytest.fixture
def humanized_content():
    """Well-humanized content"""
    return """Spent the weekend debugging our RAG pipeline. Turns out the chunking strategy was the bottleneck.

Switched from fixed-size to semantic chunking - retrieval accuracy jumped 40%.

Anyone else seeing similar patterns?"""


@pytest.fixture
def future_time():
    """Time 2 hours in the future"""
    return datetime.utcnow() + timedelta(hours=2)


@pytest.fixture
def past_time():
    """Time 10 minutes in the past"""
    return datetime.utcnow() - timedelta(minutes=10)


# Parametrized fixtures
@pytest.fixture(params=[
    ContentType.PROJECT_SHOWCASE,
    ContentType.LEARNING_UPDATE,
    ContentType.INDUSTRY_INSIGHT,
    ContentType.QUESTION_DRIVEN
])
def content_type_param(request):
    """Parametrized content types"""
    return request.param


@pytest.fixture(params=[0.7, 0.75, 0.8, 0.85])
def temperature_param(request):
    """Parametrized temperatures"""
    return request.param


@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_scheduler(sm_db_manager):
    """PostScheduler with memory store for testing"""
    from src.social_media.scheduler import PostScheduler
    scheduler = PostScheduler(db_manager=sm_db_manager, use_memory_store=True)
    yield scheduler
    if scheduler._running:
        scheduler.shutdown(wait=False)
