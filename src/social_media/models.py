"""
Social Media Automation - Database Models
SQLAlchemy models for LinkedIn and X (Twitter) automation
"""

from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime,
    Boolean, Float, Enum as SQLEnum, ForeignKey, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from cryptography.fernet import Fernet
import os
import enum

Base = declarative_base()


class Platform(enum.Enum):
    """Social media platforms"""
    LINKEDIN = "linkedin"
    TWITTER = "twitter"


class PostStatus(enum.Enum):
    """Post lifecycle status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ContentType(enum.Enum):
    """Content categories for organization"""
    PROJECT_SHOWCASE = "project_showcase"
    LEARNING_UPDATE = "learning_update"
    INDUSTRY_INSIGHT = "industry_insight"
    PERSONAL_STORY = "personal_story"
    QUESTION_DRIVEN = "question_driven"
    TUTORIAL = "tutorial"
    HOT_TAKE = "hot_take"


class User(Base):
    """User profile for social media automation"""
    __tablename__ = "sm_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    research_area = Column(Text)  # PhD research focus
    current_projects = Column(JSON)  # List of current projects
    unique_perspective = Column(Text)  # What differentiates them
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    oauth_tokens = relationship("OAuthToken", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    analytics = relationship("Analytics", back_populates="user", cascade="all, delete-orphan")
    content_templates = relationship("ContentTemplate", back_populates="user", cascade="all, delete-orphan")


class OAuthToken(Base):
    """Encrypted OAuth tokens for API access"""
    __tablename__ = "sm_oauth_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("sm_users.id"), nullable=False)
    platform = Column(SQLEnum(Platform), nullable=False)

    # Encrypted tokens (use Fernet encryption)
    access_token_encrypted = Column(Text, nullable=False)
    refresh_token_encrypted = Column(Text)
    token_secret_encrypted = Column(Text)  # For OAuth 1.0a (Twitter)

    # Token metadata
    expires_at = Column(DateTime)
    scope = Column(String(500))
    token_type = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="oauth_tokens")


class Post(Base):
    """Social media post tracking"""
    __tablename__ = "sm_posts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("sm_users.id"), nullable=False)
    platform = Column(SQLEnum(Platform), nullable=False)

    # Content
    content = Column(Text, nullable=False)
    content_type = Column(SQLEnum(ContentType))
    hashtags = Column(JSON)  # List of hashtags
    media_urls = Column(JSON)  # List of image/video URLs

    # Status tracking
    status = Column(SQLEnum(PostStatus), default=PostStatus.DRAFT)
    scheduled_time = Column(DateTime)
    published_time = Column(DateTime)

    # Platform-specific IDs
    external_post_id = Column(String(255))  # Twitter ID, LinkedIn URN, etc.
    external_url = Column(String(500))

    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # AI generation metadata
    ai_generated = Column(Boolean, default=False)
    ai_temperature = Column(Float)
    ai_prompt_version = Column(String(50))
    human_edited = Column(Boolean, default=False)

    # A/B testing
    variant_group = Column(String(50))  # For A/B testing
    test_variable = Column(String(100))  # What's being tested

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="posts")
    analytics = relationship("PostAnalytics", back_populates="post", cascade="all, delete-orphan")


class PostAnalytics(Base):
    """Detailed analytics for each post"""
    __tablename__ = "sm_post_analytics"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("sm_posts.id"), nullable=False)

    # Engagement metrics
    impressions = Column(Integer, default=0)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    retweets = Column(Integer, default=0)  # Twitter-specific
    clicks = Column(Integer, default=0)

    # Recruiter-specific metrics
    profile_views_after = Column(Integer, default=0)
    connection_requests = Column(Integer, default=0)
    recruiter_engagements = Column(Integer, default=0)

    # Calculated metrics
    engagement_rate = Column(Float)  # (likes + comments + shares) / impressions
    weighted_engagement_score = Column(Float)  # Custom weighted score

    # Time tracking
    snapshot_time = Column(DateTime, default=datetime.utcnow)
    hours_since_published = Column(Integer)

    # Relationships
    post = relationship("Post", back_populates="analytics")


class Analytics(Base):
    """User-level analytics snapshots"""
    __tablename__ = "sm_analytics"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("sm_users.id"), nullable=False)
    platform = Column(SQLEnum(Platform), nullable=False)
    snapshot_date = Column(DateTime, default=datetime.utcnow)

    # Profile metrics
    profile_views = Column(Integer, default=0)
    connections_new = Column(Integer, default=0)
    search_appearances = Column(Integer, default=0)

    # Recruiter engagement
    inmails_received = Column(Integer, default=0)
    recruiter_messages = Column(Integer, default=0)
    profile_saves = Column(Integer, default=0)
    conversations_started = Column(Integer, default=0)

    # Content performance
    posts_published_week = Column(Integer, default=0)
    avg_engagement_rate = Column(Float, default=0.0)
    top_post_id = Column(Integer)

    # Trends
    view_change_pct = Column(Float)
    engagement_trend = Column(Float)

    # Job search specific
    interviews_scheduled = Column(Integer, default=0)
    profile_to_interview_rate = Column(Float)

    # Relationships
    user = relationship("User", back_populates="analytics")


class ContentTemplate(Base):
    """Reusable content templates and styles"""
    __tablename__ = "sm_content_templates"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("sm_users.id"), nullable=False)

    name = Column(String(255), nullable=False)
    content_type = Column(SQLEnum(ContentType))
    template_text = Column(Text)

    # Style preferences
    tone = Column(String(100))  # "conversational", "professional", "technical"
    typical_length = Column(Integer)  # character count
    emoji_usage = Column(Boolean, default=False)
    hashtag_count = Column(Integer, default=2)

    # Performance tracking
    times_used = Column(Integer, default=0)
    avg_engagement = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="content_templates")


class TrendingTopic(Base):
    """Cached trending topics from Tavily"""
    __tablename__ = "sm_trending_topics"

    id = Column(Integer, primary_key=True)
    topic = Column(String(255), nullable=False)
    category = Column(String(100))  # "AI research", "job market", "tech news"

    # Topic metadata
    search_query = Column(String(500))
    source_urls = Column(JSON)
    summary = Column(Text)
    relevance_score = Column(Float)

    # Freshness tracking
    discovered_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    # Usage tracking
    times_used = Column(Integer, default=0)
    posts_generated = Column(Integer, default=0)


class ContentCalendar(Base):
    """Content planning and scheduling"""
    __tablename__ = "sm_content_calendar"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("sm_users.id"), nullable=False)

    week_number = Column(Integer)
    year = Column(Integer)
    theme = Column(String(255))  # Weekly theme

    # Content mix targets (percentages)
    project_updates_pct = Column(Integer, default=30)
    learning_shares_pct = Column(Integer, default=20)
    industry_insights_pct = Column(Integer, default=20)
    personal_stories_pct = Column(Integer, default=20)
    deep_dives_pct = Column(Integer, default=10)

    # Generated ideas
    content_ideas = Column(JSON)  # List of generated post ideas

    created_at = Column(DateTime, default=datetime.utcnow)


class ABTest(Base):
    """A/B testing experiments"""
    __tablename__ = "sm_ab_tests"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("sm_users.id"), nullable=False)

    experiment_name = Column(String(255), nullable=False)
    test_variable = Column(String(100))  # "posting_time", "content_format", "cta_type"

    # Variants
    variant_a_config = Column(JSON)
    variant_b_config = Column(JSON)

    # Results
    variant_a_impressions = Column(Integer, default=0)
    variant_a_conversions = Column(Integer, default=0)
    variant_b_impressions = Column(Integer, default=0)
    variant_b_conversions = Column(Integer, default=0)

    # Analysis
    probability_a_better = Column(Float)
    winner = Column(String(10))  # "A", "B", or "continue"
    confidence_level = Column(Float)

    # Status
    status = Column(String(50), default="running")  # "running", "completed", "paused"
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)


class OAuthState(Base):
    """Temporary OAuth state storage for CSRF protection"""
    __tablename__ = "sm_oauth_states"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("sm_users.id"), nullable=False)
    platform = Column(SQLEnum(Platform), nullable=False)

    # OAuth state parameter
    state = Column(String(100), unique=True, nullable=False)

    # Expiration tracking (states expire in 30 minutes)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    # Usage tracking
    used = Column(Boolean, default=False)
    used_at = Column(DateTime)


# Database utility functions

class DatabaseManager:
    """Manages database connection and operations"""

    def __init__(self, database_url: str = None):
        """Initialize database manager"""
        if database_url is None:
            # Default to SQLite for development
            database_url = os.getenv(
                "SOCIAL_MEDIA_DB_URL",
                "sqlite:///social_media_automation.db"
            )

        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """Get database session"""
        return self.SessionLocal()

    def drop_all_tables(self):
        """Drop all tables (use with caution!)"""
        Base.metadata.drop_all(self.engine)


# Token encryption utilities

class TokenEncryption:
    """Handles encryption/decryption of OAuth tokens"""

    def __init__(self):
        """Initialize with encryption key from environment"""
        key = os.getenv("ENCRYPTION_KEY")
        if not key:
            # Generate key if not exists (for development only)
            key = Fernet.generate_key()
            print(f"⚠️  Generated encryption key: {key.decode()}")
            print("⚠️  Set ENCRYPTION_KEY environment variable in production!")
        else:
            key = key.encode() if isinstance(key, str) else key

        self.cipher = Fernet(key)

    def encrypt(self, token: str) -> str:
        """Encrypt token"""
        if not token:
            return None
        return self.cipher.encrypt(token.encode()).decode()

    def decrypt(self, encrypted_token: str) -> str:
        """Decrypt token"""
        if not encrypted_token:
            return None
        return self.cipher.decrypt(encrypted_token.encode()).decode()


# Initialize database
db_manager = DatabaseManager()
token_encryptor = TokenEncryption()
