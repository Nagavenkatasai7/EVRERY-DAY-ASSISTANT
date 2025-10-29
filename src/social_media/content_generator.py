"""
Content Generation System for Social Media
Generates authentic, recruiter-friendly content using Claude API
"""

import re
from typing import Dict, List, Optional
from datetime import datetime
import anthropic

from config.settings import ANTHROPIC_API_KEY, MODEL_MODE
from utils.logger import get_logger
from .models import ContentType, Platform

logger = get_logger(__name__)


class ContentGenerator:
    """
    Generates social media content optimized for recruiter visibility

    Features:
    - Uses Claude 3.7 Sonnet at temperature 0.7-0.85 for natural variety
    - Removes common AI tells (excited/thrilled, emoji quartet)
    - Adapts content for LinkedIn vs Twitter/X
    - Connects external trends to user's projects
    """

    # AI detection red flags to remove/replace
    AI_RED_FLAGS = [
        "I'm excited to announce",
        "I'm thrilled to share",
        "I'm pleased to announce",
        "excited to share",
        "thrilled to announce",
        "delighted to present",
    ]

    # The "AI quartet" of emojis to limit
    AI_EMOJI_QUARTET = ["🚀", "✨", "⭐", "💡"]

    def __init__(self, model_mode: str = None):
        """Initialize content generator

        Args:
            model_mode: "api", "grok", or "local" (defaults to settings)
        """
        self.model_mode = model_mode or MODEL_MODE

        if self.model_mode == "api":
            self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            self.model = "claude-sonnet-4-20250514"
        elif self.model_mode == "grok":
            from src.grok_handler import GrokHandler
            self.grok_handler = GrokHandler()
            self.client = None
        elif self.model_mode == "local":
            from src.local_llm_handler import LocalLLMHandler
            self.local_handler = LocalLLMHandler()
            self.client = None

        logger.info(f"Content generator initialized in {self.model_mode} mode")

    def generate_project_showcase(
        self,
        project_name: str,
        project_description: str,
        technical_details: str,
        results_metrics: str,
        platform: Platform,
        user_context: Dict = None
    ) -> Dict:
        """Generate project showcase post

        Args:
            project_name: Name of the project
            project_description: Brief description
            technical_details: Technical approach and methods
            results_metrics: Specific quantifiable results
            platform: LinkedIn or Twitter
            user_context: Additional user info (research area, perspective)

        Returns:
            Dict with generated content and metadata
        """
        # Platform-specific constraints
        if platform == Platform.TWITTER:
            max_length = 280
            tone = "casual, conversational"
            structure = "Hook + key point + link"
        else:  # LinkedIn
            max_length = 1200
            tone = "professional but approachable"
            structure = "Problem → Solution → Results → Learning → Question"

        # Build context from user info
        context_str = ""
        if user_context:
            context_str = f"""
User Background:
- Research Area: {user_context.get('research_area', 'AI/ML')}
- Current Projects: {user_context.get('current_projects', [])}
- Unique Perspective: {user_context.get('unique_perspective', '')}
"""

        prompt = f"""Create a {platform.value} post about this project for a CS/AI PhD student seeking US tech jobs.

{context_str}

Project: {project_name}
Description: {project_description}
Technical Details: {technical_details}
Results: {results_metrics}

Requirements:
- Platform: {platform.value} ({max_length} chars max)
- Structure: {structure}
- Tone: {tone}
- Start with a SPECIFIC technical challenge, NOT "excited to announce"
- Include 1-2 technical terms but explain them simply
- Use contractions naturally (I'm, it's, that's)
- Include ONE genuine learning or insight
- End with a question to spark discussion
- Use max 1-2 emojis total (NOT 🚀✨⭐💡)
- Write as if explaining to a peer over coffee

Style Notes:
- First-person, conversational
- Show curiosity and learning mindset
- Connect to real-world applications
- Focus on WHY this matters, not just WHAT you built

Generate ONLY the post content, no meta-commentary.
"""

        content = self._generate_with_api(
            prompt=prompt,
            temperature=0.75,
            max_tokens=500 if platform == Platform.TWITTER else 800
        )

        # Humanization pass
        content = self._humanize_content(content)

        return {
            'content': content,
            'content_type': ContentType.PROJECT_SHOWCASE,
            'platform': platform,
            'character_count': len(content),
            'estimated_read_time': len(content.split()) / 200,  # minutes
            'ai_generated': True,
            'human_edited': False,
            'temperature': 0.75,
            'generated_at': datetime.utcnow()
        }

    def generate_learning_update(
        self,
        topic: str,
        key_insights: List[str],
        practical_application: str,
        platform: Platform,
        user_context: Dict = None
    ) -> Dict:
        """Generate learning/skill development post

        Args:
            topic: What you're learning (e.g., "RAG systems", "Multi-agent AI")
            key_insights: 2-3 key insights or takeaways
            practical_application: How you're applying this
            platform: LinkedIn or Twitter
            user_context: Additional user info

        Returns:
            Dict with generated content and metadata
        """
        insights_str = "\n".join([f"- {insight}" for insight in key_insights])

        context_str = ""
        if user_context:
            context_str = f"User's background: {user_context.get('research_area', 'AI/ML')}"

        prompt = f"""Create a {platform.value} post about learning {topic} for a PhD student.

{context_str}

Key Insights:
{insights_str}

Practical Application:
{practical_application}

Requirements:
- Platform: {platform.value}
- Share ONE specific "aha moment" or challenge overcome
- Connect theory to practice with concrete example
- Show vulnerability/confusion (learning is messy!)
- Use casual language: "turns out", "here's the thing", "I noticed"
- Include 1 question about implications or applications
- Skip "excited to learn" phrases
- Max 1 emoji

Tone: Genuine curiosity and knowledge sharing, not performative learning.

Generate ONLY the post content.
"""

        content = self._generate_with_api(
            prompt=prompt,
            temperature=0.78,
            max_tokens=400 if platform == Platform.TWITTER else 700
        )

        content = self._humanize_content(content)

        return {
            'content': content,
            'content_type': ContentType.LEARNING_UPDATE,
            'platform': platform,
            'character_count': len(content),
            'ai_generated': True,
            'human_edited': False,
            'temperature': 0.78,
            'generated_at': datetime.utcnow()
        }

    def generate_trend_commentary(
        self,
        trend_topic: str,
        trend_summary: str,
        user_projects: List[str],
        personal_angle: str,
        platform: Platform
    ) -> Dict:
        """Generate commentary on trending AI/ML topic

        Args:
            trend_topic: Trending topic (e.g., "GPT-5 announcement")
            trend_summary: Brief summary of the trend
            user_projects: User's relevant projects
            personal_angle: User's unique perspective or experience
            platform: LinkedIn or Twitter

        Returns:
            Dict with generated content and metadata
        """
        projects_str = ", ".join(user_projects)

        prompt = f"""Create a {platform.value} post reacting to this AI/ML trend:

Trend: {trend_topic}
Summary: {trend_summary}

My Context:
- Current projects: {projects_str}
- Personal angle: {personal_angle}

Requirements:
- Start with YOUR experience or observation, NOT news summary
- Connect trend to YOUR work or learning journey
- Include ONE specific implication for job seekers/students
- Ask what others think about the impact
- Be genuine: show excitement OR skepticism OR curiosity
- Avoid generic takes - make it PERSONAL
- No "breaking news" language

Tone: Thoughtful practitioner sharing perspective, not news reporter.

Generate ONLY the post content.
"""

        content = self._generate_with_api(
            prompt=prompt,
            temperature=0.80,  # Higher temp for more personality
            max_tokens=400 if platform == Platform.TWITTER else 700
        )

        content = self._humanize_content(content)

        return {
            'content': content,
            'content_type': ContentType.INDUSTRY_INSIGHT,
            'platform': platform,
            'character_count': len(content),
            'ai_generated': True,
            'human_edited': False,
            'temperature': 0.80,
            'generated_at': datetime.utcnow()
        }

    def generate_question_post(
        self,
        topic: str,
        context: str,
        your_thoughts: str,
        platform: Platform
    ) -> Dict:
        """Generate question-driven discussion post

        Args:
            topic: Topic area (e.g., "prompt engineering best practices")
            context: Why you're asking (your experience/confusion)
            your_thoughts: Your initial thoughts or hypothesis
            platform: LinkedIn or Twitter

        Returns:
            Dict with generated content and metadata
        """
        prompt = f"""Create a {platform.value} post asking about {topic}.

Context: {context}
My initial thoughts: {your_thoughts}

Requirements:
- Lead with YOUR experience/confusion/observation
- Frame a specific, debatable question
- Share your current approach/hypothesis
- Invite others to share their experience
- Be genuinely curious, not rhetorical
- Show humility - you're learning too

Tone: Peer asking for input, not expert seeking validation.

Generate ONLY the post content.
"""

        content = self._generate_with_api(
            prompt=prompt,
            temperature=0.77,
            max_tokens=350 if platform == Platform.TWITTER else 600
        )

        content = self._humanize_content(content)

        return {
            'content': content,
            'content_type': ContentType.QUESTION_DRIVEN,
            'platform': platform,
            'character_count': len(content),
            'ai_generated': True,
            'human_edited': False,
            'temperature': 0.77,
            'generated_at': datetime.utcnow()
        }

    def generate_multiple_variants(
        self,
        content_type: str,
        params: Dict,
        num_variants: int = 3
    ) -> List[Dict]:
        """Generate multiple variants for A/B testing

        Args:
            content_type: Type of content to generate
            params: Parameters for generation
            num_variants: Number of variants to create

        Returns:
            List of content dictionaries with variants
        """
        variants = []

        generation_map = {
            'project_showcase': self.generate_project_showcase,
            'learning_update': self.generate_learning_update,
            'trend_commentary': self.generate_trend_commentary,
            'question_post': self.generate_question_post
        }

        generator_func = generation_map.get(content_type)
        if not generator_func:
            raise ValueError(f"Unknown content type: {content_type}")

        for i in range(num_variants):
            variant = generator_func(**params)
            variant['variant_id'] = f"variant_{chr(65 + i)}"  # A, B, C, etc.
            variants.append(variant)

        return variants

    def _generate_with_api(
        self,
        prompt: str,
        temperature: float = 0.75,
        max_tokens: int = 500
    ) -> str:
        """Generate content using appropriate API

        Args:
            prompt: Generation prompt
            temperature: Randomness (0.7-0.85 recommended)
            max_tokens: Maximum response length

        Returns:
            Generated content string
        """
        try:
            if self.model_mode == "api":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text

            elif self.model_mode == "grok":
                messages = [{"role": "user", "content": prompt}]
                return self.grok_handler.generate_response(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )

            elif self.model_mode == "local":
                messages = [{"role": "user", "content": prompt}]
                return self.local_handler.make_api_call(
                    messages=messages,
                    system_prompt="You are a helpful assistant for generating authentic social media content.",
                    max_tokens=max_tokens
                )

        except Exception as e:
            logger.error(f"Content generation failed: {str(e)}")
            raise

    def _humanize_content(self, content: str) -> str:
        """Remove AI tells and add human touches

        Args:
            content: Generated content

        Returns:
            Humanized content
        """
        # Remove common AI phrases (case-insensitive)
        for phrase in self.AI_RED_FLAGS:
            content = re.sub(
                re.escape(phrase),
                "",
                content,
                flags=re.IGNORECASE
            )

        # Limit AI emoji quartet (keep max 1 of each)
        for emoji in self.AI_EMOJI_QUARTET:
            # Count occurrences
            count = content.count(emoji)
            if count > 1:
                # Replace all but first occurrence
                parts = content.split(emoji)
                content = emoji.join([parts[0]] + parts[1:]).replace(emoji, '', count - 1)

        # Remove excessive enthusiasm markers
        content = re.sub(r'!{2,}', '!', content)  # Multiple exclamation marks
        content = re.sub(r'\?{2,}', '?', content)  # Multiple question marks

        # Clean up whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)  # Max 2 newlines
        content = content.strip()

        return content

    def check_ai_detection_score(self, content: str) -> Dict:
        """Check how likely content is to be detected as AI-generated

        Args:
            content: Content to check

        Returns:
            Dict with detection score and issues found
        """
        issues = []
        score = 0  # 0-100, higher = more AI-like

        # Check for AI red flag phrases
        for phrase in self.AI_RED_FLAGS:
            if phrase.lower() in content.lower():
                issues.append(f"Contains AI phrase: '{phrase}'")
                score += 15

        # Check for AI emoji quartet
        emoji_count = sum(content.count(emoji) for emoji in self.AI_EMOJI_QUARTET)
        if emoji_count >= 3:
            issues.append(f"Contains {emoji_count} AI-quartet emojis")
            score += 20

        # Check for perfectly parallel structure (AI tell)
        lines = content.split('\n')
        bullet_points = [line for line in lines if line.strip().startswith(('-', '•', '*'))]
        if len(bullet_points) >= 3:
            # Check if all bullets are similar length (AI pattern)
            lengths = [len(line) for line in bullet_points]
            if max(lengths) - min(lengths) < 10:
                issues.append("Perfectly parallel bullet points (AI pattern)")
                score += 10

        # Check for generic achievements
        generic_terms = ["innovative", "cutting-edge", "revolutionary", "game-changing"]
        generic_count = sum(1 for term in generic_terms if term in content.lower())
        if generic_count >= 2:
            issues.append(f"Contains {generic_count} generic achievement terms")
            score += 10

        # Check for lack of contractions (AI tell)
        contractions = ["I'm", "it's", "don't", "can't", "won't", "that's", "there's"]
        has_contractions = any(c in content for c in contractions)
        if not has_contractions and len(content) > 100:
            issues.append("No contractions found (AI pattern)")
            score += 15

        # Cap score at 100
        score = min(score, 100)

        return {
            'ai_detection_score': score,
            'risk_level': 'HIGH' if score >= 60 else ('MEDIUM' if score >= 30 else 'LOW'),
            'issues_found': issues,
            'recommendations': self._get_humanization_tips(issues)
        }

    def _get_humanization_tips(self, issues: List[str]) -> List[str]:
        """Get specific tips to humanize content based on issues found"""
        tips = []

        if any("AI phrase" in issue for issue in issues):
            tips.append("Replace opening with a specific observation or challenge")

        if any("emoji" in issue for issue in issues):
            tips.append("Remove most emojis, keep max 1-2 total")

        if any("parallel" in issue for issue in issues):
            tips.append("Vary bullet point lengths and structures")

        if any("generic" in issue for issue in issues):
            tips.append("Replace generic terms with specific metrics or examples")

        if any("contractions" in issue for issue in issues):
            tips.append("Add contractions: it's, I'm, don't, etc.")

        tips.append("Add one detail only you would know")
        tips.append("Include a casual phrase: 'turns out', 'here's the thing'")

        return tips
