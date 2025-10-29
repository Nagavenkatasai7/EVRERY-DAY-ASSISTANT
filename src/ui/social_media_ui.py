"""
Streamlit UI for Social Media Automation
Complete interface for content generation, scheduling, analytics, and trend discovery
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import json
import secrets

# Import social media components
from src.social_media.content_generator import ContentGenerator
from src.social_media.trend_discovery import TrendDiscovery
from src.social_media.twitter_handler import TwitterHandler
from src.social_media.twitter_oauth2_handler import TwitterOAuth2Handler
from src.social_media.linkedin_handler import LinkedInHandler
from src.social_media.scheduler import PostScheduler
from src.social_media.models import (
    DatabaseManager, User, Post, PostAnalytics, Analytics,
    Platform, PostStatus, ContentType, OAuthToken, OAuthState, token_encryptor
)
from utils.logger import get_logger

logger = get_logger(__name__)


def map_content_type_display_to_enum(display_name: str) -> ContentType:
    """Map UI display names to ContentType enum values"""
    mapping = {
        "📊 Project Showcase": ContentType.PROJECT_SHOWCASE,
        "📚 Learning Update": ContentType.LEARNING_UPDATE,
        "💡 Trend Commentary": ContentType.INDUSTRY_INSIGHT,
        "❓ Question Post": ContentType.QUESTION_DRIVEN
    }
    return mapping.get(display_name, ContentType.PROJECT_SHOWCASE)


def init_session_state():
    """Initialize Streamlit session state"""
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseManager()
        # Ensure database tables are created
        st.session_state.db_manager.create_tables()

    if 'current_user_id' not in st.session_state:
        st.session_state.current_user_id = None

    if 'generated_content' not in st.session_state:
        st.session_state.generated_content = None

    if 'ai_detection_result' not in st.session_state:
        st.session_state.ai_detection_result = None

    if 'scheduler' not in st.session_state:
        st.session_state.scheduler = None

    if 'dry_run_mode' not in st.session_state:
        st.session_state.dry_run_mode = True


def social_media_automation_page():
    """Main page for social media automation"""

    # NOTE: st.set_page_config() is called in app.py, not here
    # This function is called from within a tab, so we can't call set_page_config

    # Initialize session state
    init_session_state()

    # Header
    st.title("🚀 Social Media Automation for PhD Job Seekers")
    st.markdown("""
    *Authentic, recruiter-friendly content generation powered by AI*

    ⚠️ **Compliance Note**: LinkedIn automated posting violates ToS. This tool generates content for manual posting.
    """)

    # In-page navigation using tabs
    st.markdown("---")

    # User selection at the top
    col1, col2 = st.columns([3, 1])
    with col1:
        users = get_all_users()
        if users:
            user_options = {f"{u['username']} ({u['email']})": u['id'] for u in users}
            selected_user = st.selectbox("👤 Select User Profile", list(user_options.keys()))
            st.session_state.current_user_id = user_options[selected_user]
        else:
            st.warning("⚠️ No users found. Please create a user in the Settings tab first.")
            st.session_state.current_user_id = None

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Create New User", use_container_width=True):
            st.session_state['sm_page'] = "⚙️ Settings"

    st.markdown("---")

    # Tab navigation
    page = st.radio(
        "Navigate to:",
        [
            "📝 Content Generation",
            "📅 Content Calendar",
            "📊 Analytics Dashboard",
            "🔥 Trending Topics",
            "⚙️ Settings"
        ],
        horizontal=True,
        key='sm_navigation'
    )

    # Store selected page in session state
    if 'sm_page' in st.session_state:
        page = st.session_state['sm_page']
        del st.session_state['sm_page']

    st.markdown("---")

    # Route to appropriate page
    if page == "📝 Content Generation":
        content_generation_tab()
    elif page == "📅 Content Calendar":
        content_calendar_tab()
    elif page == "📊 Analytics Dashboard":
        analytics_dashboard_tab()
    elif page == "🔥 Trending Topics":
        trending_topics_tab()
    elif page == "⚙️ Settings":
        settings_tab()


# ========================================
# CONTENT GENERATION TAB
# ========================================

def content_generation_tab():
    """Content generation interface"""
    st.header("📝 Content Generation")

    if not st.session_state.current_user_id:
        st.error("⚠️ Please select or create a user in the Settings page first.")
        return

    # Get user profile
    user = get_user_profile(st.session_state.current_user_id)
    if not user:
        st.error("User not found.")
        return

    # Display user context
    with st.expander("👤 Your Profile Context", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Research Area**: {user.get('research_area', 'Not set')}")
        with col2:
            st.info(f"**Projects**: {', '.join(user.get('current_projects', [])) if user.get('current_projects') else 'None'}")
        if user.get('unique_perspective'):
            st.info(f"**Unique Perspective**: {user['unique_perspective']}")

    st.markdown("---")

    # Content type selector
    col1, col2 = st.columns([2, 1])

    with col1:
        content_type = st.selectbox(
            "Content Type",
            [
                "📊 Project Showcase",
                "📚 Learning Update",
                "💡 Trend Commentary",
                "❓ Question Post"
            ],
            help="Choose the type of content you want to generate"
        )

    with col2:
        platform = st.selectbox(
            "Platform",
            ["Twitter/X", "LinkedIn"],
            help="Twitter: 280 chars, can auto-post. LinkedIn: 1200 chars, manual only."
        )

    platform_enum = Platform.TWITTER if platform == "Twitter/X" else Platform.LINKEDIN

    st.markdown("---")

    # Map display name to enum
    content_type_enum = map_content_type_display_to_enum(content_type)

    # Content-specific forms
    if "Project Showcase" in content_type:
        project_showcase_form(user, platform_enum, content_type_enum)
    elif "Learning Update" in content_type:
        learning_update_form(user, platform_enum, content_type_enum)
    elif "Trend Commentary" in content_type:
        trend_commentary_form(user, platform_enum, content_type_enum)
    elif "Question Post" in content_type:
        question_post_form(user, platform_enum, content_type_enum)

    # Display generated content
    if st.session_state.generated_content:
        display_generated_content(platform_enum)


def project_showcase_form(user: Dict, platform: Platform, content_type: ContentType):
    """Form for project showcase content"""
    st.subheader("📊 Project Showcase")

    with st.form("project_showcase_form"):
        col1, col2 = st.columns(2)

        with col1:
            project_name = st.text_input(
                "Project Name *",
                placeholder="e.g., Multi-Agent RAG System"
            )

            project_description = st.text_area(
                "Brief Description *",
                placeholder="What does your project do?",
                height=100
            )

        with col2:
            technical_details = st.text_area(
                "Technical Approach *",
                placeholder="Key technologies, methods, or techniques used",
                height=100
            )

            results_metrics = st.text_area(
                "Results & Metrics *",
                placeholder="Quantifiable results (e.g., 40% faster, 95% accuracy)",
                height=100
            )

        st.markdown("**Advanced Options**")
        col3, col4 = st.columns(2)
        with col3:
            temperature = st.slider("Creativity Level", 0.5, 1.0, 0.75, 0.05,
                                   help="Higher = more creative, Lower = more focused")
        with col4:
            num_variants = st.number_input("Generate Variants", 1, 5, 1,
                                          help="Create multiple versions for A/B testing")

        submitted = st.form_submit_button("✨ Generate Content", use_container_width=True)

        if submitted:
            if not all([project_name, project_description, technical_details, results_metrics]):
                st.error("Please fill in all required fields (*)")
            else:
                with st.spinner("Generating authentic content..."):
                    try:
                        generator = ContentGenerator()

                        user_context = {
                            'research_area': user.get('research_area', ''),
                            'current_projects': user.get('current_projects', []),
                            'unique_perspective': user.get('unique_perspective', '')
                        }

                        if num_variants == 1:
                            result = generator.generate_project_showcase(
                                project_name=project_name,
                                project_description=project_description,
                                technical_details=technical_details,
                                results_metrics=results_metrics,
                                platform=platform,
                                user_context=user_context
                            )
                            result['content_type'] = content_type
                            st.session_state.generated_content = [result]
                        else:
                            params = {
                                'project_name': project_name,
                                'project_description': project_description,
                                'technical_details': technical_details,
                                'results_metrics': results_metrics,
                                'platform': platform,
                                'user_context': user_context
                            }
                            results = generator.generate_multiple_variants(
                                'project_showcase', params, num_variants
                            )
                            # Add content_type to all variants
                            for result in results:
                                result['content_type'] = content_type
                            st.session_state.generated_content = results

                        st.success("✅ Content generated successfully!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Generation failed: {str(e)}")
                        logger.error(f"Content generation error: {str(e)}")


def learning_update_form(user: Dict, platform: Platform, content_type: ContentType):
    """Form for learning update content"""
    st.subheader("📚 Learning Update")

    with st.form("learning_update_form"):
        topic = st.text_input(
            "What are you learning? *",
            placeholder="e.g., RAG optimization techniques, Prompt engineering"
        )

        col1, col2 = st.columns(2)

        with col1:
            insight1 = st.text_input("Key Insight #1 *", placeholder="First major takeaway")
            insight2 = st.text_input("Key Insight #2", placeholder="Second takeaway (optional)")

        with col2:
            insight3 = st.text_input("Key Insight #3", placeholder="Third takeaway (optional)")
            practical_app = st.text_area(
                "How are you applying this? *",
                placeholder="Concrete example of how you're using this learning",
                height=100
            )

        submitted = st.form_submit_button("✨ Generate Content", use_container_width=True)

        if submitted:
            if not topic or not insight1 or not practical_app:
                st.error("Please fill in all required fields (*)")
            else:
                with st.spinner("Generating learning update..."):
                    try:
                        generator = ContentGenerator()

                        insights = [i for i in [insight1, insight2, insight3] if i]

                        user_context = {
                            'research_area': user.get('research_area', ''),
                        }

                        result = generator.generate_learning_update(
                            topic=topic,
                            key_insights=insights,
                            practical_application=practical_app,
                            platform=platform,
                            user_context=user_context
                        )
                        result['content_type'] = content_type

                        st.session_state.generated_content = [result]
                        st.success("✅ Content generated successfully!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Generation failed: {str(e)}")
                        logger.error(f"Content generation error: {str(e)}")


def trend_commentary_form(user: Dict, platform: Platform, content_type: ContentType):
    """Form for trend commentary content"""
    st.subheader("💡 Trend Commentary")

    with st.form("trend_commentary_form"):
        col1, col2 = st.columns(2)

        with col1:
            trend_topic = st.text_input(
                "Trending Topic *",
                placeholder="e.g., GPT-5 announcement, Claude 4 release"
            )

            trend_summary = st.text_area(
                "Brief Summary *",
                placeholder="What's the trend about?",
                height=100
            )

        with col2:
            user_projects = st.text_input(
                "Relevant Projects",
                value=", ".join(user.get('current_projects', [])),
                help="Your projects related to this trend"
            )

            personal_angle = st.text_area(
                "Your Perspective *",
                placeholder="What's your unique take or experience with this?",
                height=100
            )

        submitted = st.form_submit_button("✨ Generate Content", use_container_width=True)

        if submitted:
            if not all([trend_topic, trend_summary, personal_angle]):
                st.error("Please fill in all required fields (*)")
            else:
                with st.spinner("Generating trend commentary..."):
                    try:
                        generator = ContentGenerator()

                        projects_list = [p.strip() for p in user_projects.split(',')] if user_projects else []

                        result = generator.generate_trend_commentary(
                            trend_topic=trend_topic,
                            trend_summary=trend_summary,
                            user_projects=projects_list,
                            personal_angle=personal_angle,
                            platform=platform
                        )
                        result['content_type'] = content_type

                        st.session_state.generated_content = [result]
                        st.success("✅ Content generated successfully!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Generation failed: {str(e)}")
                        logger.error(f"Content generation error: {str(e)}")


def question_post_form(user: Dict, platform: Platform, content_type: ContentType):
    """Form for question-driven post"""
    st.subheader("❓ Question Post")

    with st.form("question_post_form"):
        topic = st.text_input(
            "Topic/Question Area *",
            placeholder="e.g., Prompt engineering best practices"
        )

        context = st.text_area(
            "Why are you asking? *",
            placeholder="Your experience or confusion that prompted this question",
            height=100
        )

        your_thoughts = st.text_area(
            "Your Initial Thoughts *",
            placeholder="What's your current approach or hypothesis?",
            height=100
        )

        submitted = st.form_submit_button("✨ Generate Content", use_container_width=True)

        if submitted:
            if not all([topic, context, your_thoughts]):
                st.error("Please fill in all required fields (*)")
            else:
                with st.spinner("Generating question post..."):
                    try:
                        generator = ContentGenerator()

                        result = generator.generate_question_post(
                            topic=topic,
                            context=context,
                            your_thoughts=your_thoughts,
                            platform=platform
                        )
                        result['content_type'] = content_type

                        st.session_state.generated_content = [result]
                        st.success("✅ Content generated successfully!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"❌ Generation failed: {str(e)}")
                        logger.error(f"Content generation error: {str(e)}")


def display_generated_content(platform: Platform):
    """Display generated content with editing and posting options"""
    st.markdown("---")
    st.subheader("✨ Generated Content")

    if not st.session_state.generated_content:
        return

    # Handle multiple variants
    variants = st.session_state.generated_content

    if len(variants) > 1:
        st.info(f"📊 Generated {len(variants)} variants for A/B testing")

    for idx, content_data in enumerate(variants):
        variant_label = content_data.get('variant_id', f'Variant {idx + 1}')

        with st.expander(f"📄 {variant_label}", expanded=(idx == 0)):
            # Character count and AI detection
            col1, col2, col3 = st.columns(3)

            char_count = content_data['character_count']
            max_chars = 280 if platform == Platform.TWITTER else 1200
            char_percentage = (char_count / max_chars) * 100

            with col1:
                char_color = "green" if char_percentage < 90 else ("orange" if char_percentage < 100 else "red")
                st.metric("Character Count", f"{char_count}/{max_chars}")

            with col2:
                # Run AI detection
                if st.button(f"🔍 Check AI Detection", key=f"detect_{idx}"):
                    generator = ContentGenerator()
                    detection = generator.check_ai_detection_score(content_data['content'])
                    st.session_state.ai_detection_result = detection

            with col3:
                if st.session_state.ai_detection_result:
                    risk_level = st.session_state.ai_detection_result['risk_level']
                    risk_color = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}[risk_level]
                    st.metric("AI Detection Risk", risk_level)

            # Display AI detection details
            if st.session_state.ai_detection_result:
                detection = st.session_state.ai_detection_result

                if detection['issues_found']:
                    st.warning("⚠️ AI Detection Issues Found:")
                    for issue in detection['issues_found']:
                        st.markdown(f"- {issue}")

                    st.info("💡 **Humanization Tips:**")
                    for tip in detection['recommendations']:
                        st.markdown(f"- {tip}")

            # Content display and editing
            st.markdown("**Preview:**")
            edited_content = st.text_area(
                "Content",
                value=content_data['content'],
                height=200,
                key=f"content_{idx}",
                label_visibility="collapsed"
            )

            # Update content if edited
            if edited_content != content_data['content']:
                content_data['content'] = edited_content
                content_data['character_count'] = len(edited_content)
                content_data['human_edited'] = True

            # Action buttons
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if platform == Platform.TWITTER:
                    if st.button(f"🐦 Post to Twitter", key=f"post_twitter_{idx}", use_container_width=True):
                        post_to_twitter(content_data)
                else:
                    if st.button(f"📋 Copy for LinkedIn", key=f"copy_linkedin_{idx}", use_container_width=True):
                        st.code(edited_content, language=None)
                        st.success("✅ Content ready to copy! Paste manually on LinkedIn.")

            with col2:
                if st.button(f"💾 Save as Draft", key=f"save_draft_{idx}", use_container_width=True):
                    save_post_draft(content_data, platform)

            with col3:
                if st.button(f"📅 Schedule Post", key=f"schedule_{idx}", use_container_width=True):
                    st.session_state[f'schedule_modal_{idx}'] = True

            with col4:
                if st.button(f"🔄 Regenerate", key=f"regen_{idx}", use_container_width=True):
                    st.session_state.generated_content = None
                    st.rerun()

            # Schedule modal
            if st.session_state.get(f'schedule_modal_{idx}'):
                schedule_post_modal(content_data, platform, idx)


def schedule_post_modal(content_data: Dict, platform: Platform, idx: int):
    """Modal for scheduling a post"""
    st.markdown("---")
    st.subheader("📅 Schedule Post")

    col1, col2 = st.columns(2)

    with col1:
        schedule_date = st.date_input(
            "Date",
            value=datetime.now().date() + timedelta(days=1),
            min_value=datetime.now().date()
        )

    with col2:
        schedule_time = st.time_input("Time", value=datetime.now().time())

    scheduled_datetime = datetime.combine(schedule_date, schedule_time)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ Confirm Schedule", use_container_width=True):
            if platform == Platform.LINKEDIN:
                st.error("⚠️ LinkedIn automated posting violates ToS. Please post manually.")
            else:
                schedule_twitter_post(content_data, scheduled_datetime)
                st.session_state[f'schedule_modal_{idx}'] = False
                st.rerun()

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state[f'schedule_modal_{idx}'] = False
            st.rerun()


# ========================================
# CONTENT CALENDAR TAB
# ========================================

def content_calendar_tab():
    """Content calendar and scheduling interface"""
    st.header("📅 Content Calendar")

    if not st.session_state.current_user_id:
        st.error("⚠️ Please select or create a user first.")
        return

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📆 Calendar View", "📝 All Posts", "⏱️ Scheduled Posts"])

    with tab1:
        calendar_view()

    with tab2:
        all_posts_view()

    with tab3:
        scheduled_posts_view()


def calendar_view():
    """Calendar visualization of posts"""
    st.subheader("📆 Content Calendar")

    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From", value=datetime.now().date() - timedelta(days=30))
    with col2:
        end_date = st.date_input("To", value=datetime.now().date() + timedelta(days=30))

    # Get posts in date range
    posts = get_posts_in_range(st.session_state.current_user_id, start_date, end_date)

    if not posts:
        st.info("No posts found in this date range.")
        return

    # Create calendar visualization
    df = pd.DataFrame(posts)

    # Group by date
    if 'scheduled_time' in df.columns:
        df['date'] = pd.to_datetime(df['scheduled_time']).dt.date
        posts_by_date = df.groupby('date').size().reset_index(name='count')

        fig = px.bar(
            posts_by_date,
            x='date',
            y='count',
            title="Posts by Date",
            labels={'date': 'Date', 'count': 'Number of Posts'},
            color='count',
            color_continuous_scale='Blues'
        )

        st.plotly_chart(fig, use_container_width=True)

    # Display posts by status
    st.subheader("Posts by Status")
    status_counts = df['status'].value_counts()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📝 Drafts", status_counts.get('DRAFT', 0))
    with col2:
        st.metric("📅 Scheduled", status_counts.get('SCHEDULED', 0))
    with col3:
        st.metric("✅ Published", status_counts.get('PUBLISHED', 0))
    with col4:
        st.metric("❌ Failed", status_counts.get('FAILED', 0))


def all_posts_view():
    """List all posts with filters"""
    st.subheader("📝 All Posts")

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.multiselect(
            "Status",
            ["DRAFT", "SCHEDULED", "PUBLISHED", "FAILED", "CANCELLED"],
            default=["DRAFT", "SCHEDULED", "PUBLISHED"]
        )

    with col2:
        platform_filter = st.multiselect(
            "Platform",
            ["TWITTER", "LINKEDIN"],
            default=["TWITTER", "LINKEDIN"]
        )

    with col3:
        content_type_filter = st.multiselect(
            "Content Type",
            ["PROJECT_SHOWCASE", "LEARNING_UPDATE", "INDUSTRY_INSIGHT", "QUESTION_DRIVEN"],
            default=[]
        )

    # Get filtered posts
    posts = get_filtered_posts(
        st.session_state.current_user_id,
        status_filter,
        platform_filter,
        content_type_filter
    )

    if not posts:
        st.info("No posts match the selected filters.")
        return

    # Display posts
    for post in posts:
        display_post_card(post)


def display_post_card(post: Dict):
    """Display a post card with actions"""
    status_colors = {
        'DRAFT': '🟡',
        'SCHEDULED': '🔵',
        'PUBLISHED': '🟢',
        'FAILED': '🔴',
        'CANCELLED': '⚫'
    }

    status_badge = status_colors.get(post['status'], '⚪')

    with st.expander(
        f"{status_badge} {post['platform']} - {post['content_type']} - {post.get('created_at', 'N/A')}",
        expanded=False
    ):
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"**Content:**")
            st.text_area(
                "Content",
                value=post['content'],
                height=150,
                key=f"post_content_{post['id']}",
                label_visibility="collapsed",
                disabled=True
            )

            if post.get('external_url'):
                st.markdown(f"[🔗 View on {post['platform']}]({post['external_url']})")

        with col2:
            st.markdown(f"**Status:** {post['status']}")
            st.markdown(f"**Platform:** {post['platform']}")
            st.markdown(f"**Type:** {post['content_type']}")

            if post.get('scheduled_time'):
                st.markdown(f"**Scheduled:** {post['scheduled_time']}")

            if post.get('published_time'):
                st.markdown(f"**Published:** {post['published_time']}")

            if post.get('error_message'):
                st.error(f"**Error:** {post['error_message']}")

        # Action buttons
        col1, col2, col3 = st.columns(3)

        with col1:
            if post['status'] in ['DRAFT', 'FAILED']:
                if st.button(f"📅 Schedule", key=f"schedule_post_{post['id']}", use_container_width=True):
                    st.session_state[f'schedule_existing_{post["id"]}'] = True
                    st.rerun()

        with col2:
            if post['status'] == 'SCHEDULED':
                if st.button(f"❌ Cancel", key=f"cancel_post_{post['id']}", use_container_width=True):
                    cancel_scheduled_post(post['id'])
                    st.rerun()

            if post['status'] == 'FAILED':
                if st.button(f"🔄 Retry", key=f"retry_post_{post['id']}", use_container_width=True):
                    retry_failed_post(post['id'])
                    st.rerun()

        with col3:
            if st.button(f"🗑️ Delete", key=f"delete_post_{post['id']}", use_container_width=True):
                delete_post(post['id'])
                st.rerun()


def scheduled_posts_view():
    """View and manage scheduled posts"""
    st.subheader("⏱️ Scheduled Posts")

    # Initialize scheduler if needed
    if not st.session_state.scheduler:
        st.session_state.scheduler = PostScheduler(st.session_state.db_manager)
        st.session_state.scheduler.start()

    # Get scheduled posts
    scheduled = st.session_state.scheduler.get_scheduled_posts(
        st.session_state.current_user_id
    )

    if not scheduled:
        st.info("No posts currently scheduled.")
        return

    # Display scheduled posts
    for post in scheduled:
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.markdown(f"**{post['platform']}** - {post['content_type']}")
                st.caption(post['content'][:100] + "..." if len(post['content']) > 100 else post['content'])

            with col2:
                st.markdown(f"**Scheduled:**")
                st.markdown(f"{post['scheduled_time']}")

            with col3:
                if st.button(f"✏️ Edit", key=f"edit_sched_{post['post_id']}", use_container_width=True):
                    st.session_state[f'edit_schedule_{post["post_id"]}'] = True

                if st.button(f"❌ Cancel", key=f"cancel_sched_{post['post_id']}", use_container_width=True):
                    st.session_state.scheduler.cancel_scheduled_post(post['post_id'])
                    st.success(f"Cancelled post {post['post_id']}")
                    st.rerun()

            st.markdown("---")


# ========================================
# ANALYTICS DASHBOARD TAB
# ========================================

def analytics_dashboard_tab():
    """Analytics and performance metrics"""
    st.header("📊 Analytics Dashboard")

    if not st.session_state.current_user_id:
        st.error("⚠️ Please select or create a user first.")
        return

    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From", value=datetime.now().date() - timedelta(days=30))
    with col2:
        end_date = st.date_input("To", value=datetime.now().date())

    # Get analytics data
    analytics = get_analytics_data(st.session_state.current_user_id, start_date, end_date)

    if not analytics:
        st.info("No analytics data available for this period.")
        return

    # Key metrics
    st.subheader("📈 Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Posts",
            analytics.get('total_posts', 0),
            delta=analytics.get('posts_change', 0)
        )

    with col2:
        st.metric(
            "Avg Engagement Rate",
            f"{analytics.get('avg_engagement_rate', 0):.1f}%",
            delta=f"{analytics.get('engagement_change', 0):.1f}%"
        )

    with col3:
        st.metric(
            "Total Impressions",
            f"{analytics.get('total_impressions', 0):,}",
            delta=analytics.get('impressions_change', 0)
        )

    with col4:
        st.metric(
            "Total Engagement",
            analytics.get('total_engagement', 0),
            delta=analytics.get('engagement_delta', 0)
        )

    st.markdown("---")

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Engagement Over Time")
        if 'engagement_timeline' in analytics:
            df = pd.DataFrame(analytics['engagement_timeline'])
            fig = px.line(
                df,
                x='date',
                y='engagement',
                title="Engagement Trend",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📈 Content Type Performance")
        if 'content_type_stats' in analytics:
            df = pd.DataFrame(analytics['content_type_stats'])
            fig = px.bar(
                df,
                x='content_type',
                y='avg_engagement',
                title="Average Engagement by Content Type",
                color='avg_engagement',
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Top performing posts
    st.subheader("🏆 Top Performing Posts")

    if 'top_posts' in analytics:
        for post in analytics['top_posts'][:5]:
            with st.container():
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"**{post['platform']}** - {post['content_type']}")
                    st.caption(post['content'][:150] + "..." if len(post['content']) > 150 else post['content'])

                with col2:
                    st.metric("Engagement", post['total_engagement'])
                    st.metric("Impressions", post['impressions'])

                st.markdown("---")

    # Best posting times heatmap
    st.subheader("⏰ Best Posting Times")
    if 'posting_times' in analytics:
        df = pd.DataFrame(analytics['posting_times'])
        fig = px.density_heatmap(
            df,
            x='hour',
            y='day_of_week',
            z='engagement',
            title="Engagement by Day and Hour",
            labels={'hour': 'Hour of Day', 'day_of_week': 'Day of Week', 'engagement': 'Avg Engagement'}
        )
        st.plotly_chart(fig, use_container_width=True)


# ========================================
# TRENDING TOPICS TAB
# ========================================

def trending_topics_tab():
    """Discover and explore trending topics"""
    st.header("🔥 Trending Topics")

    if not st.session_state.current_user_id:
        st.error("⚠️ Please select or create a user first.")
        return

    # Check for Tavily API key
    tavily_key = os.getenv('TAVILY_API_KEY')
    if not tavily_key:
        st.error("⚠️ TAVILY_API_KEY not configured. Please add it to your .env file.")
        st.info("Get your free API key at: https://tavily.com")
        return

    # Category selector
    col1, col2 = st.columns([2, 1])

    with col1:
        categories = st.multiselect(
            "Select Categories",
            ["ai_research", "job_market", "tech_news", "tools_frameworks"],
            default=["ai_research", "job_market"]
        )

    with col2:
        if st.button("🔄 Refresh Trends", use_container_width=True):
            st.session_state['trends_cache'] = None

    if not categories:
        st.warning("Please select at least one category.")
        return

    # Get trends
    with st.spinner("Discovering trending topics..."):
        trends = get_trending_topics(categories)

    if not trends:
        st.info("No trends found. Try different categories or refresh.")
        return

    # Get user profile for relevance scoring
    user = get_user_profile(st.session_state.current_user_id)

    # Display trends by category
    for category, category_trends in trends.items():
        st.subheader(f"📊 {category.replace('_', ' ').title()}")

        for idx, trend in enumerate(category_trends):
            with st.expander(
                f"📰 {trend['topic']} (Relevance: {trend['relevance_score']:.0%})",
                expanded=(idx == 0)
            ):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"**Summary:**")
                    st.markdown(trend['summary'])

                    if trend.get('url'):
                        st.markdown(f"[🔗 Read More]({trend['url']})")

                with col2:
                    st.metric("Relevance", f"{trend['relevance_score']:.0%}")

                    if st.button(
                        "✨ Generate Content",
                        key=f"gen_trend_{category}_{idx}",
                        use_container_width=True
                    ):
                        generate_content_from_trend(trend, user)

                    if st.button(
                        "🚀 Generate & Post Now",
                        key=f"gen_post_trend_{category}_{idx}",
                        use_container_width=True,
                        type="primary"
                    ):
                        # Store trend info in session state for persistent UI
                        st.session_state[f'posting_trend_{category}_{idx}'] = True
                        st.session_state[f'current_trend_{category}_{idx}'] = trend
                        st.rerun()

                # Show posting UI if this trend is selected for posting
                if st.session_state.get(f'posting_trend_{category}_{idx}', False):
                    generate_and_post_from_trend_ui(
                        trend=st.session_state[f'current_trend_{category}_{idx}'],
                        user=user,
                        trend_key=f"{category}_{idx}"
                    )

        st.markdown("---")


def generate_content_from_trend(trend: Dict, user: Dict):
    """Generate content based on a trending topic"""
    try:
        generator = ContentGenerator()

        # Select platform
        platform = Platform.TWITTER  # Default

        with st.spinner("🤖 Generating content from trend..."):
            result = generator.generate_trend_commentary(
                trend_topic=trend['topic'],
                trend_summary=trend['summary'],
                user_projects=user.get('current_projects', []),
                personal_angle=user.get('unique_perspective', 'As a PhD student'),
                platform=platform
            )

        st.session_state.generated_content = [result]

        # Show preview immediately
        st.success("✅ Content generated successfully!")
        st.markdown("### 📝 Generated Content Preview:")
        st.info(result['content'])

        st.markdown("**📊 Content Details:**")
        col1, col2, col3 = st.columns(3)
        with col1:
            # Convert platform enum to string if needed
            platform_value = result.get('platform', 'Twitter')
            if hasattr(platform_value, 'value'):
                platform_value = platform_value.value
            elif hasattr(platform_value, 'name'):
                platform_value = platform_value.name
            st.metric("Platform", str(platform_value))
        with col2:
            st.metric("Length", f"{len(result['content'])} chars")
        with col3:
            ai_score = result.get('ai_detection_score', 0)
            st.metric("AI Detection", f"{ai_score:.0%}",
                     delta="Low" if ai_score < 0.3 else "High",
                     delta_color="normal" if ai_score < 0.3 else "inverse")

        st.info("💡 Tip: Content also saved to 'Content Generation' tab for editing before posting")

    except Exception as e:
        st.error(f"❌ Failed to generate content: {str(e)}")
        logger.error(f"Trend content generation error: {str(e)}")


def generate_and_post_from_trend_ui(trend: Dict, user: Dict, trend_key: str):
    """Persistent UI for generating and posting content from trend"""
    st.markdown("---")
    st.markdown("### 🎯 Select Platforms to Post:")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        post_to_twitter = st.checkbox(
            "🐦 Twitter/X",
            value=st.session_state.get(f'select_tw_{trend_key}', True),
            key=f"select_tw_{trend_key}"
        )

    with col2:
        post_to_linkedin = st.checkbox(
            "💼 LinkedIn",
            value=st.session_state.get(f'select_li_{trend_key}', True),
            key=f"select_li_{trend_key}"
        )

    if not post_to_twitter and not post_to_linkedin:
        st.warning("⚠️ Please select at least one platform to post to")

    with col3:
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Confirm & Post", key=f"confirm_post_{trend_key}", type="primary", use_container_width=True):
                if post_to_twitter or post_to_linkedin:
                    # Execute the posting
                    generate_and_post_from_trend(trend, user, post_to_twitter, post_to_linkedin)
                    # Clear the session state after posting
                    st.session_state[f'posting_trend_{trend_key}'] = False
                    st.rerun()

        with col_b:
            if st.button("❌ Cancel", key=f"cancel_post_{trend_key}", use_container_width=True):
                # Clear the session state
                st.session_state[f'posting_trend_{trend_key}'] = False
                st.rerun()


def generate_and_post_from_trend(trend: Dict, user: Dict, post_to_twitter: bool = True, post_to_linkedin: bool = True):
    """Generate content from trend and post immediately to selected platforms"""
    try:
        # Check OAuth credentials for selected platforms
        session = st.session_state.db_manager.get_session()

        linkedin_token = None

        if post_to_linkedin:
            linkedin_token = session.query(OAuthToken).filter(
                OAuthToken.user_id == st.session_state.current_user_id,
                OAuthToken.platform == Platform.LINKEDIN
            ).first()

            if not linkedin_token:
                session.close()
                st.error("⚠️ LinkedIn OAuth not configured! Please add credentials in Settings → LinkedIn OAuth.")
                return

        # Generate content
        generator = ContentGenerator()

        with st.spinner("🤖 Generating content from trend..."):
            # Generate for Twitter first (shorter content)
            twitter_result = generator.generate_trend_commentary(
                trend_topic=trend['topic'],
                trend_summary=trend['summary'],
                user_projects=user.get('current_projects', []),
                personal_angle=user.get('unique_perspective', 'As a PhD student'),
                platform=Platform.TWITTER
            )

            # Generate for LinkedIn (can be longer and more professional)
            linkedin_result = generator.generate_trend_commentary(
                trend_topic=trend['topic'],
                trend_summary=trend['summary'],
                user_projects=user.get('current_projects', []),
                personal_angle=user.get('unique_perspective', 'As a PhD student'),
                platform=Platform.LINKEDIN
            )

        # Track posting results
        posting_results = []

        # Post to Twitter if selected
        if post_to_twitter:
            with st.spinner("🚀 Posting to Twitter..."):
                try:
                    # Create post record
                    twitter_post = Post(
                        user_id=st.session_state.current_user_id,
                        platform=Platform.TWITTER,
                        content=twitter_result['content'],
                        content_type=ContentType.INDUSTRY_INSIGHT,
                        status=PostStatus.DRAFT,
                        ai_generated=True,
                        ai_temperature=twitter_result.get('temperature', 0.75)
                    )
                    session.add(twitter_post)
                    session.commit()
                    session.refresh(twitter_post)

                    # Use Twitter OAuth 1.0a credentials from .env
                    api_key = os.getenv('TWITTER_API_KEY')
                    api_secret = os.getenv('TWITTER_API_SECRET')
                    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
                    access_secret = os.getenv('TWITTER_ACCESS_SECRET')

                    if not all([api_key, api_secret, access_token, access_secret]):
                        session.close()
                        st.error("⚠️ Twitter credentials not configured in .env file!")
                        posting_results.append(("Twitter", False, "Credentials not configured"))
                        return

                    twitter_handler = TwitterHandler(
                        api_key=api_key,
                        api_secret=api_secret,
                        access_token=access_token,
                        access_secret=access_secret
                    )

                    # Post tweet
                    tweet_result = twitter_handler.create_tweet(twitter_result['content'])

                    if tweet_result.get('success'):
                        # Update post status
                        twitter_post.status = PostStatus.PUBLISHED
                        twitter_post.published_time = datetime.utcnow()
                        twitter_post.external_post_id = tweet_result['tweet_id']
                        twitter_post.external_url = tweet_result.get('url')
                        session.commit()
                        posting_results.append(("Twitter", True, tweet_result['tweet_id']))
                    else:
                        error_msg = tweet_result.get('error', 'Failed to post')
                        posting_results.append(("Twitter", False, error_msg))

                except Exception as e:
                    logger.error(f"Twitter posting error: {str(e)}")
                    posting_results.append(("Twitter", False, str(e)))

        # Post to LinkedIn if selected
        if post_to_linkedin:
            with st.spinner("🚀 Posting to LinkedIn..."):
                try:
                    # Create post record
                    linkedin_post = Post(
                        user_id=st.session_state.current_user_id,
                        platform=Platform.LINKEDIN,
                        content=linkedin_result['content'],
                        content_type=ContentType.INDUSTRY_INSIGHT,
                        status=PostStatus.DRAFT,
                        ai_generated=True,
                        ai_temperature=linkedin_result.get('temperature', 0.75)
                    )
                    session.add(linkedin_post)
                    session.commit()
                    session.refresh(linkedin_post)

                    # Get LinkedIn credentials
                    client_id = os.getenv('LINKEDIN_CLIENT_ID')
                    client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')

                    if not client_id or not client_secret:
                        posting_results.append(("LinkedIn", False, "Client credentials not configured"))
                    else:
                        # Decrypt access token
                        access_token = None
                        if linkedin_token.access_token_encrypted:
                            access_token = token_encryptor.decrypt(linkedin_token.access_token_encrypted)

                        if not access_token:
                            posting_results.append(("LinkedIn", False, "Access token not found"))
                        else:
                            # Initialize LinkedIn handler
                            linkedin_handler = LinkedInHandler(
                                client_id=client_id,
                                client_secret=client_secret,
                                access_token=access_token
                            )

                            # Post to LinkedIn
                            post_urn = linkedin_handler.create_post(
                                content=linkedin_result['content'],
                                visibility="PUBLIC"
                            )

                            if post_urn:
                                # Update post status
                                linkedin_post.status = PostStatus.PUBLISHED
                                linkedin_post.published_at = datetime.utcnow()
                                linkedin_post.external_id = post_urn
                                session.commit()
                                posting_results.append(("LinkedIn", True, post_urn))
                            else:
                                posting_results.append(("LinkedIn", False, "Failed to post"))

                except Exception as e:
                    logger.error(f"LinkedIn posting error: {str(e)}")
                    posting_results.append(("LinkedIn", False, str(e)))

        session.close()

        # Display results
        st.markdown("### 📊 Posting Results:")

        success_count = sum(1 for _, success, _ in posting_results if success)

        for platform, success, result in posting_results:
            if success:
                st.success(f"✅ Posted to {platform}! ID: {result}")
            else:
                st.error(f"❌ Failed to post to {platform}: {result}")

        if success_count == len(posting_results):
            st.balloons()
            st.success(f"🎉 Successfully posted to all {len(posting_results)} platform(s)!")
        elif success_count > 0:
            st.warning(f"⚠️ Posted to {success_count}/{len(posting_results)} platform(s)")

    except Exception as e:
        st.error(f"❌ Failed to generate and post: {str(e)}")
        logger.error(f"Generate and post error: {str(e)}")


# ========================================
# SETTINGS TAB
# ========================================

def settings_tab():
    """Settings and configuration"""
    st.header("⚙️ Settings")

    tab1, tab2, tab3, tab4 = st.tabs([
        "👤 User Profile",
        "🔑 API Credentials",
        "💼 LinkedIn OAuth 2.0",
        "🗄️ Database Management"
    ])

    with tab1:
        user_profile_settings()

    with tab2:
        api_credentials_settings()

    with tab3:
        linkedin_oauth_settings()

    with tab4:
        database_management_settings()

    # Note: Twitter uses OAuth 1.0a credentials from .env file - no frontend configuration needed


def user_profile_settings():
    """User profile management"""
    st.subheader("👤 User Profile Management")

    # Create new user
    with st.expander("➕ Create New User", expanded=False):
        with st.form("create_user_form"):
            col1, col2 = st.columns(2)

            with col1:
                username = st.text_input("Username *")
                email = st.text_input("Email *")
                full_name = st.text_input("Full Name")

            with col2:
                research_area = st.text_area(
                    "Research Area *",
                    placeholder="e.g., AI/ML, Natural Language Processing"
                )

                current_projects = st.text_area(
                    "Current Projects (comma-separated)",
                    placeholder="Project 1, Project 2, Project 3"
                )

            unique_perspective = st.text_area(
                "Unique Perspective",
                placeholder="What makes your approach or experience unique?"
            )

            submitted = st.form_submit_button("Create User", use_container_width=True)

            if submitted:
                if not all([username, email, research_area]):
                    st.error("Please fill in all required fields (*)")
                else:
                    projects_list = [p.strip() for p in current_projects.split(',')] if current_projects else []

                    success = create_user(
                        username=username,
                        email=email,
                        full_name=full_name,
                        research_area=research_area,
                        current_projects=projects_list,
                        unique_perspective=unique_perspective
                    )

                    if success:
                        st.success("✅ User created successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to create user. Username or email may already exist.")

    # Edit existing user
    if st.session_state.current_user_id:
        st.markdown("---")
        st.subheader("✏️ Edit Current User")

        user = get_user_profile(st.session_state.current_user_id)

        if user:
            with st.form("edit_user_form"):
                col1, col2 = st.columns(2)

                with col1:
                    full_name = st.text_input("Full Name", value=user.get('full_name', ''))
                    research_area = st.text_area("Research Area", value=user.get('research_area', ''))

                with col2:
                    current_projects = st.text_area(
                        "Current Projects (comma-separated)",
                        value=', '.join(user.get('current_projects', []))
                    )
                    unique_perspective = st.text_area(
                        "Unique Perspective",
                        value=user.get('unique_perspective', '')
                    )

                submitted = st.form_submit_button("Update Profile", use_container_width=True)

                if submitted:
                    projects_list = [p.strip() for p in current_projects.split(',')] if current_projects else []

                    success = update_user_profile(
                        st.session_state.current_user_id,
                        full_name=full_name,
                        research_area=research_area,
                        current_projects=projects_list,
                        unique_perspective=unique_perspective
                    )

                    if success:
                        st.success("✅ Profile updated successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to update profile.")


def api_credentials_settings():
    """API credentials configuration"""
    st.subheader("🔑 API Credentials")

    st.info("""
    Configure your API keys for content generation and trend discovery.
    These are read from your .env file.
    """)

    # Check API keys
    col1, col2 = st.columns(2)

    with col1:
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        st.markdown("**Anthropic API Key**")
        if anthropic_key:
            st.success("✅ Configured")
        else:
            st.error("❌ Not configured")
            st.code("ANTHROPIC_API_KEY=your_key_here", language="bash")

    with col2:
        tavily_key = os.getenv('TAVILY_API_KEY')
        st.markdown("**Tavily API Key**")
        if tavily_key:
            st.success("✅ Configured")
        else:
            st.error("❌ Not configured")
            st.code("TAVILY_API_KEY=your_key_here", language="bash")

    st.markdown("---")

    # Posting preferences
    st.subheader("⚙️ Posting Preferences")

    with st.form("posting_preferences"):
        dry_run = st.checkbox(
            "Dry Run Mode",
            value=st.session_state.dry_run_mode,
            help="When enabled, posts will be logged but not actually published"
        )

        default_temperature = st.slider(
            "Default Creativity Level",
            0.5, 1.0, 0.75, 0.05,
            help="Default temperature for content generation"
        )

        submitted = st.form_submit_button("Save Preferences", use_container_width=True)

        if submitted:
            st.session_state.dry_run_mode = dry_run
            st.success("✅ Preferences saved!")


def twitter_oauth_settings():
    """Twitter OAuth 2.0 configuration"""
    st.subheader("🐦 Twitter OAuth 2.0 Setup")

    st.warning("""
    ⚠️ **Important**: This uses Twitter API v2 with OAuth 2.0 Client Credentials.
    You need a Twitter Developer account with API v2 access.
    """)

    st.markdown("""
    ### Setup Steps:
    1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
    2. Create a new app or use an existing one
    3. Navigate to "Keys and tokens" tab
    4. Find **OAuth 2.0 Client ID** and **Client Secret**
    5. Add them below or to your .env file
    """)

    st.info("""
    **OAuth 2.0 vs OAuth 1.0a:**
    - OAuth 2.0 uses Client ID + Client Secret (recommended)
    - OAuth 1.0a uses Consumer Key/Secret + Access Token/Secret (legacy)
    - This app now uses OAuth 2.0 for better security and simpler authentication
    """)

    # Check if credentials are in .env
    col1, col2 = st.columns(2)

    with col1:
        client_id_env = os.getenv('TWITTER_CLIENT_ID')
        st.markdown("**OAuth 2.0 Client ID**")
        if client_id_env:
            st.success("✅ Configured in .env")
            st.caption(f"ID: {client_id_env[:10]}...")
        else:
            st.error("❌ Not configured in .env")

    with col2:
        client_secret_env = os.getenv('TWITTER_CLIENT_SECRET')
        st.markdown("**OAuth 2.0 Client Secret**")
        if client_secret_env:
            st.success("✅ Configured in .env")
            st.caption("Secret: ********")
        else:
            st.error("❌ Not configured in .env")

    st.markdown("---")

    # OAuth 2.0 credentials for current user
    if st.session_state.current_user_id:
        st.subheader("🔐 User OAuth 2.0 Credentials")

        st.markdown("""
        Enter your Twitter OAuth 2.0 credentials below. These will be encrypted and stored securely for this user.
        """)

        with st.form("twitter_oauth2_form"):
            client_id = st.text_input(
                "OAuth 2.0 Client ID",
                type="password",
                help="Get this from Twitter Developer Portal → Your App → Keys and tokens"
            )
            client_secret = st.text_input(
                "OAuth 2.0 Client Secret",
                type="password",
                help="Get this from Twitter Developer Portal → Your App → Keys and tokens"
            )

            # Optional: Bearer Token (if they have it pre-generated)
            bearer_token = st.text_input(
                "Bearer Token (Optional)",
                type="password",
                help="If you have a pre-generated Bearer Token, enter it here. Otherwise, it will be generated automatically."
            )

            submitted = st.form_submit_button("Save OAuth 2.0 Credentials", use_container_width=True)

            if submitted:
                if client_id and client_secret:
                    success = save_oauth_tokens(
                        st.session_state.current_user_id,
                        Platform.TWITTER,
                        client_id,  # Access token field stores Client ID
                        client_secret,  # Access secret field stores Client Secret
                        bearer_token if bearer_token else None
                    )

                    if success:
                        st.success("✅ OAuth 2.0 credentials saved securely!")
                        st.info("You can now use automated posting features!")
                    else:
                        st.error("❌ Failed to save credentials.")
                else:
                    st.error("Please provide both Client ID and Client Secret.")

        # Show current status
        st.markdown("---")
        st.markdown("**Current Configuration Status:**")

        session = st.session_state.db_manager.get_session()
        token_record = session.query(OAuthToken).filter(
            OAuthToken.user_id == st.session_state.current_user_id,
            OAuthToken.platform == Platform.TWITTER
        ).first()
        session.close()

        if token_record:
            st.success("✅ Twitter OAuth 2.0 credentials configured for this user")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Platform", "Twitter/X")
            with col2:
                st.metric("Status", "Ready")
        else:
            st.warning("⚠️ No OAuth 2.0 credentials configured yet")


def linkedin_oauth_settings():
    """LinkedIn OAuth 2.0 configuration"""
    import secrets
    import urllib.parse

    st.subheader("💼 LinkedIn Account Connection")

    st.info("Connect your LinkedIn account to enable posting to LinkedIn.")

    # Check if credentials are in .env
    col1, col2 = st.columns(2)

    with col1:
        client_id_env = os.getenv('LINKEDIN_CLIENT_ID')
        st.markdown("**OAuth 2.0 Client ID**")
        if client_id_env:
            st.success("✅ Configured in .env")
            st.caption(f"ID: {client_id_env[:10]}...")
        else:
            st.error("❌ Not configured in .env")

    with col2:
        client_secret_env = os.getenv('LINKEDIN_CLIENT_SECRET')
        st.markdown("**OAuth 2.0 Client Secret**")
        if client_secret_env:
            st.success("✅ Configured in .env")
            st.caption("Secret: ********")
        else:
            st.error("❌ Not configured in .env")

    st.markdown("---")

    # OAuth 2.0 credentials for current user
    if st.session_state.current_user_id:
        st.subheader("🔐 LinkedIn Authorization")

        # Check for OAuth callback (code parameter in URL)
        try:
            query_params = st.query_params
            auth_code = query_params.get("code")
            state_param = query_params.get("state")

            if auth_code and state_param:
                # Verify state parameter from database (CSRF protection)
                session = st.session_state.db_manager.get_session()
                state_record = session.query(OAuthState).filter(
                    OAuthState.user_id == st.session_state.current_user_id,
                    OAuthState.platform == Platform.LINKEDIN,
                    OAuthState.state == state_param,
                    OAuthState.used == False,
                    OAuthState.expires_at > datetime.utcnow()
                ).first()

                if state_record:
                    st.info("🔄 Processing LinkedIn authorization...")

                    # Mark state as used
                    state_record.used = True
                    state_record.used_at = datetime.utcnow()
                    session.commit()

                    # Exchange code for access token
                    if client_id_env and client_secret_env:
                        from src.social_media.linkedin_handler import LinkedInHandler

                        linkedin_handler = LinkedInHandler(
                            client_id=client_id_env,
                            client_secret=client_secret_env
                        )

                        redirect_uri = os.getenv('LINKEDIN_REDIRECT_URI', 'http://localhost:8502/callback')

                        with st.spinner("Exchanging authorization code for access token..."):
                            access_token = linkedin_handler.get_access_token(
                                authorization_code=auth_code,
                                redirect_uri=redirect_uri
                            )

                        if access_token:
                            # Get token expiry from handler
                            token_expires_at = linkedin_handler.token_expires_at

                            # Save to database with scope and expiry
                            success = save_oauth_tokens(
                                st.session_state.current_user_id,
                                Platform.LINKEDIN,
                                access_token,  # Access token
                                client_secret_env,  # Client Secret
                                client_id_env,  # Client ID
                                scope="openid profile email w_member_social",
                                expires_at=token_expires_at
                            )

                            if success:
                                st.success("✅ LinkedIn authorization successful! Access token saved.")
                                st.warning("⚠️ Remember: Automated LinkedIn posting may violate ToS!")
                                # Clear query parameters
                                st.query_params.clear()
                                # Clean up expired states
                                session.query(OAuthState).filter(
                                    OAuthState.expires_at < datetime.utcnow()
                                ).delete()
                                session.commit()
                                session.close()
                                st.rerun()
                            else:
                                session.close()
                                st.error("❌ Failed to save access token to database.")
                        else:
                            session.close()
                            st.error("❌ Failed to exchange authorization code for access token.")
                    else:
                        session.close()
                        st.error("❌ LinkedIn Client ID or Secret not configured in .env!")
                else:
                    session.close()
                    st.error("❌ Invalid state parameter. Possible CSRF attack detected!")
                    logger.error(f"Invalid OAuth state: {state_param}")
        except Exception as e:
            logger.error(f"LinkedIn OAuth callback error: {str(e)}")

        # Show current status
        session = st.session_state.db_manager.get_session()
        token_record = session.query(OAuthToken).filter(
            OAuthToken.user_id == st.session_state.current_user_id,
            OAuthToken.platform == Platform.LINKEDIN
        ).first()
        session.close()

        if token_record:
            st.success("✅ LinkedIn OAuth 2.0 credentials configured")
            st.warning("⚠️ Use automated posting responsibly and at your own risk")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Platform", "LinkedIn")
            with col2:
                st.metric("Status", "Authorized")
            with col3:
                if st.button("🔄 Re-authorize", use_container_width=True):
                    # Will generate new auth URL below
                    pass
        else:
            st.warning("⚠️ Not authorized yet. Click button below to authorize.")

        st.markdown("---")

        # Generate Authorization URL
        if client_id_env and client_secret_env:
            if st.button("🔐 Login with LinkedIn", type="primary", use_container_width=True):
                # Generate state parameter for CSRF protection
                state = secrets.token_urlsafe(32)

                # Save state to database for persistence across redirects
                session = st.session_state.db_manager.get_session()
                try:
                    # Clean up old unused states for this user
                    session.query(OAuthState).filter(
                        OAuthState.user_id == st.session_state.current_user_id,
                        OAuthState.platform == Platform.LINKEDIN,
                        OAuthState.used == False
                    ).delete()

                    # Create new state record with 30-minute expiration
                    state_record = OAuthState(
                        user_id=st.session_state.current_user_id,
                        platform=Platform.LINKEDIN,
                        state=state,
                        expires_at=datetime.utcnow() + timedelta(minutes=30)
                    )
                    session.add(state_record)
                    session.commit()
                    logger.info(f"Saved OAuth state to database: {state[:10]}...")
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to save OAuth state: {str(e)}")
                    st.error("❌ Failed to initialize OAuth flow. Please try again.")
                    session.close()
                    st.stop()
                finally:
                    session.close()

                # Generate authorization URL
                from src.social_media.linkedin_handler import LinkedInHandler

                linkedin_handler = LinkedInHandler(
                    client_id=client_id_env,
                    client_secret=client_secret_env
                )

                redirect_uri = os.getenv('LINKEDIN_REDIRECT_URI', 'http://localhost:8502/callback')
                scope = "openid profile email w_member_social"

                auth_url = linkedin_handler.generate_authorization_url(
                    redirect_uri=redirect_uri,
                    state=state,
                    scope=scope
                )

                # Auto-redirect using st.link_button or markdown
                st.markdown(f"""
                **[Click here to authorize on LinkedIn]({auth_url})**

                You'll be redirected back after authorization.
                """)
        else:
            st.error("❌ Please configure LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in your .env file first!")


def database_management_settings():
    """Database management tools"""
    st.subheader("🗄️ Database Management")

    st.warning("⚠️ Use these tools carefully. Some actions cannot be undone.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Database Statistics**")

        stats = get_database_stats()

        st.metric("Total Users", stats.get('users', 0))
        st.metric("Total Posts", stats.get('posts', 0))
        st.metric("Scheduled Posts", stats.get('scheduled', 0))

    with col2:
        st.markdown("**Database Actions**")

        if st.button("🧹 Clear Old Posts (>90 days)", use_container_width=True):
            count = clear_old_posts(90)
            st.success(f"✅ Deleted {count} old posts")

        if st.button("📥 Export Data", use_container_width=True):
            export_data()

        if st.button("🔄 Reset Scheduler", use_container_width=True):
            if st.session_state.scheduler:
                st.session_state.scheduler.shutdown()
                st.session_state.scheduler = None
            st.success("✅ Scheduler reset")


# ========================================
# HELPER FUNCTIONS
# ========================================

def get_all_users() -> List[Dict]:
    """Get all users from database"""
    try:
        session = st.session_state.db_manager.get_session()
        users = session.query(User).all()

        result = [
            {
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'full_name': u.full_name,
                'research_area': u.research_area
            }
            for u in users
        ]

        session.close()
        return result

    except Exception as e:
        logger.error(f"Failed to get users: {str(e)}")
        return []


def get_user_profile(user_id: int) -> Optional[Dict]:
    """Get user profile by ID"""
    try:
        session = st.session_state.db_manager.get_session()
        user = session.query(User).filter(User.id == user_id).first()

        if not user:
            return None

        result = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'research_area': user.research_area,
            'current_projects': user.current_projects or [],
            'unique_perspective': user.unique_perspective
        }

        session.close()
        return result

    except Exception as e:
        logger.error(f"Failed to get user profile: {str(e)}")
        return None


def create_user(username: str, email: str, full_name: str, research_area: str,
                current_projects: List[str], unique_perspective: str) -> bool:
    """Create a new user"""
    try:
        session = st.session_state.db_manager.get_session()

        user = User(
            username=username,
            email=email,
            full_name=full_name,
            research_area=research_area,
            current_projects=current_projects,
            unique_perspective=unique_perspective
        )

        session.add(user)
        session.commit()
        session.close()

        return True

    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}")
        return False


def update_user_profile(user_id: int, **kwargs) -> bool:
    """Update user profile"""
    try:
        session = st.session_state.db_manager.get_session()
        user = session.query(User).filter(User.id == user_id).first()

        if not user:
            return False

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        session.commit()
        session.close()

        return True

    except Exception as e:
        logger.error(f"Failed to update user: {str(e)}")
        return False


def save_post_draft(content_data: Dict, platform: Platform) -> bool:
    """Save post as draft"""
    try:
        session = st.session_state.db_manager.get_session()

        post = Post(
            user_id=st.session_state.current_user_id,
            platform=platform,
            content=content_data['content'],
            content_type=content_data.get('content_type'),
            status=PostStatus.DRAFT,
            ai_generated=content_data.get('ai_generated', True),
            ai_temperature=content_data.get('temperature'),
            human_edited=content_data.get('human_edited', False)
        )

        session.add(post)
        session.commit()
        session.close()

        st.success(f"✅ Saved as draft (ID: {post.id})")
        return True

    except Exception as e:
        logger.error(f"Failed to save draft: {str(e)}")
        st.error(f"❌ Failed to save draft: {str(e)}")
        return False


def post_to_twitter(content_data: Dict):
    """Post content to Twitter"""
    if st.session_state.dry_run_mode:
        st.info("🔍 Dry run mode: Post would be published to Twitter")
        st.code(content_data['content'])
        return

    try:
        # Use Twitter OAuth 1.0a credentials from .env
        session = st.session_state.db_manager.get_session()

        api_key = os.getenv('TWITTER_API_KEY')
        api_secret = os.getenv('TWITTER_API_SECRET')
        access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        access_secret = os.getenv('TWITTER_ACCESS_SECRET')

        if not all([api_key, api_secret, access_token, access_secret]):
            st.error("⚠️ Twitter credentials not configured in .env file!")
            session.close()
            return

        twitter = TwitterHandler(
            api_key=api_key,
            api_secret=api_secret,
            access_token=access_token,
            access_secret=access_secret,
            dry_run=False
        )

        # Post tweet
        result = twitter.create_tweet(content=content_data['content'])

        if result['success']:
            # Save to database
            post = Post(
                user_id=st.session_state.current_user_id,
                platform=Platform.TWITTER,
                content=content_data['content'],
                content_type=content_data.get('content_type'),
                status=PostStatus.PUBLISHED,
                published_time=datetime.utcnow(),
                external_post_id=result.get('tweet_id'),
                external_url=result.get('url'),
                ai_generated=content_data.get('ai_generated', True),
                human_edited=content_data.get('human_edited', False)
            )

            session.add(post)
            session.commit()

            st.success(f"✅ Posted to Twitter! [View Tweet]({result['url']})")
        else:
            st.error(f"❌ Failed to post: {result.get('error', 'Unknown error')}")

        session.close()

    except Exception as e:
        logger.error(f"Twitter post failed: {str(e)}")
        st.error(f"❌ Failed to post to Twitter: {str(e)}")


def post_to_linkedin(content_data: Dict):
    """Post content to LinkedIn"""
    try:
        session = st.session_state.db_manager.get_session()

        # Check LinkedIn OAuth credentials
        token_record = session.query(OAuthToken).filter(
            OAuthToken.user_id == st.session_state.current_user_id,
            OAuthToken.platform == Platform.LINKEDIN
        ).first()

        if not token_record:
            st.error("⚠️ LinkedIn OAuth tokens not configured. Please add them in Settings.")
            session.close()
            return

        # Decrypt tokens
        # For LinkedIn: access_token_encrypted = access token, token_secret_encrypted = client secret, refresh_token = client ID
        access_token = token_encryptor.decrypt(token_record.access_token_encrypted)
        client_secret = token_encryptor.decrypt(token_record.token_secret_encrypted)
        client_id = None
        if token_record.refresh_token_encrypted:
            client_id = token_encryptor.decrypt(token_record.refresh_token_encrypted)

        # Get credentials from environment if not in user tokens
        if not client_id:
            client_id = os.getenv('LINKEDIN_CLIENT_ID')
        if not client_secret:
            client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')

        if not client_id or not client_secret or not access_token:
            st.error("⚠️ LinkedIn OAuth credentials not fully configured.")
            session.close()
            return

        # Create LinkedIn handler
        linkedin = LinkedInHandler(
            client_id=client_id,
            client_secret=client_secret,
            access_token=access_token
        )

        # Post to LinkedIn
        post_urn = linkedin.create_post(content=content_data['content'])

        if post_urn:
            # Save to database
            post = Post(
                user_id=st.session_state.current_user_id,
                platform=Platform.LINKEDIN,
                content=content_data['content'],
                content_type=content_data.get('content_type'),
                status=PostStatus.PUBLISHED,
                published_time=datetime.utcnow(),
                external_post_id=post_urn,
                ai_generated=content_data.get('ai_generated', True),
                human_edited=content_data.get('human_edited', False)
            )

            session.add(post)
            session.commit()

            st.success(f"✅ Posted to LinkedIn! URN: {post_urn}")
        else:
            st.error("❌ Failed to post to LinkedIn")

        session.close()

    except Exception as e:
        logger.error(f"LinkedIn post failed: {str(e)}")
        st.error(f"❌ Failed to post to LinkedIn: {str(e)}")


def post_to_multiple_platforms(content_data: Dict, platforms: List[Platform]):
    """Post content to multiple platforms simultaneously"""
    results = {}

    for platform in platforms:
        try:
            if platform == Platform.TWITTER:
                post_to_twitter(content_data)
                results['twitter'] = {'success': True}
            elif platform == Platform.LINKEDIN:
                post_to_linkedin(content_data)
                results['linkedin'] = {'success': True}
        except Exception as e:
            results[platform.value.lower()] = {'success': False, 'error': str(e)}

    # Show summary
    success_count = sum(1 for r in results.values() if r.get('success'))
    st.info(f"📊 Posted to {success_count}/{len(platforms)} platforms successfully")

    return results


def schedule_twitter_post(content_data: Dict, scheduled_time: datetime):
    """Schedule a Twitter post"""
    try:
        # Save post first
        session = st.session_state.db_manager.get_session()

        post = Post(
            user_id=st.session_state.current_user_id,
            platform=Platform.TWITTER,
            content=content_data['content'],
            content_type=content_data.get('content_type'),
            status=PostStatus.SCHEDULED,
            scheduled_time=scheduled_time,
            ai_generated=content_data.get('ai_generated', True),
            human_edited=content_data.get('human_edited', False)
        )

        session.add(post)
        session.commit()
        post_id = post.id
        session.close()

        # Initialize scheduler if needed
        if not st.session_state.scheduler:
            st.session_state.scheduler = PostScheduler(st.session_state.db_manager)
            st.session_state.scheduler.start()

        # Schedule post
        job_id = st.session_state.scheduler.schedule_post(
            post_id=post_id,
            scheduled_time=scheduled_time,
            user_id=st.session_state.current_user_id
        )

        st.success(f"✅ Post scheduled for {scheduled_time}")

    except Exception as e:
        logger.error(f"Failed to schedule post: {str(e)}")
        st.error(f"❌ Failed to schedule: {str(e)}")


def get_posts_in_range(user_id: int, start_date, end_date) -> List[Dict]:
    """Get posts in date range"""
    try:
        session = st.session_state.db_manager.get_session()

        posts = session.query(Post).filter(
            Post.user_id == user_id,
            Post.created_at >= datetime.combine(start_date, datetime.min.time()),
            Post.created_at <= datetime.combine(end_date, datetime.max.time())
        ).all()

        result = [
            {
                'id': p.id,
                'content': p.content,
                'platform': p.platform.value,
                'status': p.status.value,
                'content_type': p.content_type.value if p.content_type else None,
                'scheduled_time': p.scheduled_time,
                'published_time': p.published_time,
                'created_at': p.created_at
            }
            for p in posts
        ]

        session.close()
        return result

    except Exception as e:
        logger.error(f"Failed to get posts: {str(e)}")
        return []


def get_filtered_posts(user_id: int, status_filter: List[str],
                       platform_filter: List[str], content_type_filter: List[str]) -> List[Dict]:
    """Get filtered posts"""
    try:
        session = st.session_state.db_manager.get_session()

        query = session.query(Post).filter(Post.user_id == user_id)

        if status_filter:
            query = query.filter(Post.status.in_([PostStatus[s] for s in status_filter]))

        if platform_filter:
            query = query.filter(Post.platform.in_([Platform[p] for p in platform_filter]))

        if content_type_filter:
            query = query.filter(Post.content_type.in_([ContentType[c] for c in content_type_filter]))

        posts = query.order_by(Post.created_at.desc()).limit(50).all()

        result = [
            {
                'id': p.id,
                'content': p.content,
                'platform': p.platform.value,
                'status': p.status.value,
                'content_type': p.content_type.value if p.content_type else None,
                'scheduled_time': p.scheduled_time,
                'published_time': p.published_time,
                'created_at': p.created_at,
                'external_url': p.external_url,
                'error_message': p.error_message
            }
            for p in posts
        ]

        session.close()
        return result

    except Exception as e:
        logger.error(f"Failed to get filtered posts: {str(e)}")
        return []


def cancel_scheduled_post(post_id: int):
    """Cancel a scheduled post"""
    try:
        if st.session_state.scheduler:
            st.session_state.scheduler.cancel_scheduled_post(post_id)
            st.success(f"✅ Post {post_id} cancelled")
        else:
            st.error("Scheduler not initialized")

    except Exception as e:
        logger.error(f"Failed to cancel post: {str(e)}")
        st.error(f"❌ Failed to cancel: {str(e)}")


def retry_failed_post(post_id: int):
    """Retry a failed post"""
    try:
        session = st.session_state.db_manager.get_session()
        post = session.query(Post).filter(Post.id == post_id).first()

        if post:
            post.status = PostStatus.DRAFT
            post.retry_count = 0
            post.error_message = None
            session.commit()
            st.success(f"✅ Post {post_id} reset to draft. You can now reschedule it.")

        session.close()

    except Exception as e:
        logger.error(f"Failed to retry post: {str(e)}")
        st.error(f"❌ Failed to retry: {str(e)}")


def delete_post(post_id: int):
    """Delete a post"""
    try:
        session = st.session_state.db_manager.get_session()
        post = session.query(Post).filter(Post.id == post_id).first()

        if post:
            session.delete(post)
            session.commit()
            st.success(f"✅ Post {post_id} deleted")

        session.close()

    except Exception as e:
        logger.error(f"Failed to delete post: {str(e)}")
        st.error(f"❌ Failed to delete: {str(e)}")


def get_analytics_data(user_id: int, start_date, end_date) -> Dict:
    """Get analytics data for user"""
    try:
        session = st.session_state.db_manager.get_session()

        # Get posts in range
        posts = session.query(Post).filter(
            Post.user_id == user_id,
            Post.status == PostStatus.PUBLISHED,
            Post.published_time >= datetime.combine(start_date, datetime.min.time()),
            Post.published_time <= datetime.combine(end_date, datetime.max.time())
        ).all()

        if not posts:
            session.close()
            return {}

        # Calculate metrics
        total_posts = len(posts)

        # Get analytics for posts
        post_ids = [p.id for p in posts]
        analytics = session.query(PostAnalytics).filter(
            PostAnalytics.post_id.in_(post_ids)
        ).all()

        total_impressions = sum(a.impressions for a in analytics)
        total_engagement = sum(a.likes + a.comments + a.shares for a in analytics)
        avg_engagement_rate = (total_engagement / total_impressions * 100) if total_impressions > 0 else 0

        # Top posts
        top_posts = sorted(
            posts,
            key=lambda p: sum(a.likes + a.comments + a.shares for a in analytics if a.post_id == p.id),
            reverse=True
        )[:5]

        result = {
            'total_posts': total_posts,
            'total_impressions': total_impressions,
            'total_engagement': total_engagement,
            'avg_engagement_rate': avg_engagement_rate,
            'top_posts': [
                {
                    'content': p.content,
                    'platform': p.platform.value,
                    'content_type': p.content_type.value if p.content_type else None,
                    'total_engagement': sum(a.likes + a.comments + a.shares for a in analytics if a.post_id == p.id),
                    'impressions': sum(a.impressions for a in analytics if a.post_id == p.id)
                }
                for p in top_posts
            ]
        }

        session.close()
        return result

    except Exception as e:
        logger.error(f"Failed to get analytics: {str(e)}")
        return {}


def get_trending_topics(categories: List[str]) -> Dict[str, List[Dict]]:
    """Get trending topics by category"""
    try:
        if 'trends_cache' not in st.session_state or st.session_state.trends_cache is None:
            discovery = TrendDiscovery(db_manager=st.session_state.db_manager)
            trends = discovery.discover_weekly_trends(
                categories=categories,
                max_results_per_category=5
            )
            st.session_state.trends_cache = trends

        return st.session_state.trends_cache

    except Exception as e:
        logger.error(f"Failed to get trends: {str(e)}")
        st.error(f"❌ Failed to discover trends: {str(e)}")
        return {}


def save_oauth_tokens(user_id: int, platform: Platform, access_token: str, access_secret: str, bearer_token: str = None, scope: str = None, expires_at: datetime = None) -> bool:
    """Save OAuth tokens (supports both OAuth 1.0a and OAuth 2.0)"""
    try:
        session = st.session_state.db_manager.get_session()

        # Check if token exists
        token_record = session.query(OAuthToken).filter(
            OAuthToken.user_id == user_id,
            OAuthToken.platform == platform
        ).first()

        if token_record:
            # Update existing
            token_record.access_token_encrypted = token_encryptor.encrypt(access_token)
            token_record.token_secret_encrypted = token_encryptor.encrypt(access_secret)
            if bearer_token:
                token_record.refresh_token_encrypted = token_encryptor.encrypt(bearer_token)
            if scope:
                token_record.scope = scope
            if expires_at:
                token_record.expires_at = expires_at
            token_record.updated_at = datetime.utcnow()
        else:
            # Create new
            token_record = OAuthToken(
                user_id=user_id,
                platform=platform,
                access_token_encrypted=token_encryptor.encrypt(access_token),
                token_secret_encrypted=token_encryptor.encrypt(access_secret),
                refresh_token_encrypted=token_encryptor.encrypt(bearer_token) if bearer_token else None,
                scope=scope,
                expires_at=expires_at
            )
            session.add(token_record)

        session.commit()
        session.close()

        return True

    except Exception as e:
        logger.error(f"Failed to save OAuth tokens: {str(e)}")
        return False


def get_database_stats() -> Dict:
    """Get database statistics"""
    try:
        session = st.session_state.db_manager.get_session()

        users_count = session.query(User).count()
        posts_count = session.query(Post).count()
        scheduled_count = session.query(Post).filter(Post.status == PostStatus.SCHEDULED).count()

        session.close()

        return {
            'users': users_count,
            'posts': posts_count,
            'scheduled': scheduled_count
        }

    except Exception as e:
        logger.error(f"Failed to get database stats: {str(e)}")
        return {'users': 0, 'posts': 0, 'scheduled': 0}


def clear_old_posts(days: int) -> int:
    """Clear posts older than specified days"""
    try:
        session = st.session_state.db_manager.get_session()

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        old_posts = session.query(Post).filter(
            Post.created_at < cutoff_date,
            Post.status.in_([PostStatus.PUBLISHED, PostStatus.FAILED, PostStatus.CANCELLED])
        ).all()

        count = len(old_posts)

        for post in old_posts:
            session.delete(post)

        session.commit()
        session.close()

        return count

    except Exception as e:
        logger.error(f"Failed to clear old posts: {str(e)}")
        return 0


def export_data():
    """Export database data"""
    try:
        session = st.session_state.db_manager.get_session()

        posts = session.query(Post).all()

        data = []
        for post in posts:
            data.append({
                'id': post.id,
                'user_id': post.user_id,
                'platform': post.platform.value,
                'content': post.content,
                'content_type': post.content_type.value if post.content_type else None,
                'status': post.status.value,
                'scheduled_time': str(post.scheduled_time) if post.scheduled_time else None,
                'published_time': str(post.published_time) if post.published_time else None,
                'external_url': post.external_url,
                'created_at': str(post.created_at)
            })

        session.close()

        df = pd.DataFrame(data)
        csv = df.to_csv(index=False)

        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"social_media_posts_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    except Exception as e:
        logger.error(f"Failed to export data: {str(e)}")
        st.error(f"❌ Failed to export: {str(e)}")


# ========================================
# MAIN ENTRY POINT
# ========================================

if __name__ == "__main__":
    social_media_automation_page()
