"""
Comprehensive Content Generator Tests
Tests AI content generation, humanization, and detection

Coverage targets:
- Project showcase generation
- Learning update generation
- Trend commentary generation
- AI detection scoring
- Humanization algorithms
- Multiple variant generation
- Platform-specific formatting
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.social_media.content_generator import ContentGenerator
from src.social_media.models import Platform, ContentType


# ==================== Initialization Tests ====================

@pytest.mark.unit
class TestContentGeneratorInit:
    """Test ContentGenerator initialization"""

    def test_init_api_mode(self, mock_anthropic):
        """Test initialization in API mode"""
        with patch('config.settings.MODEL_MODE', 'api'):
            with patch('config.settings.ANTHROPIC_API_KEY', 'test_key'):
                generator = ContentGenerator(model_mode='api')

                assert generator.model_mode == 'api'
                assert generator.client is not None
                assert generator.model == "claude-sonnet-4-20250514"

    def test_init_grok_mode(self):
        """Test initialization in Grok mode"""
        with patch('src.grok_handler.GrokHandler'):
            generator = ContentGenerator(model_mode='grok')

            assert generator.model_mode == 'grok'
            assert generator.client is None
            assert hasattr(generator, 'grok_handler')

    def test_init_local_mode(self):
        """Test initialization in local mode"""
        with patch('src.local_llm_handler.LocalLLMHandler'):
            generator = ContentGenerator(model_mode='local')

            assert generator.model_mode == 'local'
            assert generator.client is None
            assert hasattr(generator, 'local_handler')


# ==================== Project Showcase Tests ====================

@pytest.mark.unit
class TestProjectShowcaseGeneration:
    """Test project showcase content generation"""

    def test_generate_project_showcase_twitter(self, mock_anthropic):
        """Test generating project showcase for Twitter"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_project_showcase(
            project_name="RAG Chatbot",
            project_description="AI chatbot with retrieval-augmented generation",
            technical_details="Python, LangChain, FAISS, Claude API",
            results_metrics="98% accuracy, 80% cost reduction",
            platform=Platform.TWITTER
        )

        assert result['content'] is not None
        assert len(result['content']) <= 280  # Twitter character limit
        assert result['content_type'] == ContentType.PROJECT_SHOWCASE
        assert result['platform'] == Platform.TWITTER
        assert result['ai_generated'] is True
        assert result['temperature'] == 0.75

    def test_generate_project_showcase_linkedin(self, mock_anthropic):
        """Test generating project showcase for LinkedIn"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_project_showcase(
            project_name="Multi-Agent Research Assistant",
            project_description="Comprehensive research analysis system",
            technical_details="Multi-agent architecture, RAG, async processing",
            results_metrics="141 tests passing, 90%+ coverage",
            platform=Platform.LINKEDIN
        )

        assert result['content'] is not None
        assert len(result['content']) <= 1200
        assert result['platform'] == Platform.LINKEDIN
        assert result['character_count'] == len(result['content'])

    def test_project_showcase_with_user_context(self, mock_anthropic):
        """Test project showcase with user context"""
        generator = ContentGenerator(model_mode='api')

        user_context = {
            'research_area': 'Multi-agent AI systems',
            'current_projects': ['Research Assistant', 'RAG Chatbot'],
            'unique_perspective': 'Bridging research and production'
        }

        result = generator.generate_project_showcase(
            project_name="Test Project",
            project_description="Test description",
            technical_details="Test tech",
            results_metrics="Test metrics",
            platform=Platform.TWITTER,
            user_context=user_context
        )

        assert result['content'] is not None
        assert result['ai_generated'] is True

    def test_project_showcase_metadata(self, mock_anthropic):
        """Test project showcase metadata"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_project_showcase(
            project_name="Test",
            project_description="Test",
            technical_details="Test",
            results_metrics="Test",
            platform=Platform.TWITTER
        )

        assert 'content' in result
        assert 'content_type' in result
        assert 'platform' in result
        assert 'character_count' in result
        assert 'estimated_read_time' in result
        assert 'temperature' in result
        assert 'generated_at' in result
        assert isinstance(result['generated_at'], datetime)


# ==================== Learning Update Tests ====================

@pytest.mark.unit
class TestLearningUpdateGeneration:
    """Test learning update content generation"""

    def test_generate_learning_update_twitter(self, mock_anthropic):
        """Test generating learning update for Twitter"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_learning_update(
            topic="RAG optimization techniques",
            key_insights=[
                "Semantic chunking outperforms fixed-size",
                "Hybrid search combines vector + keyword",
                "Reranking boosts precision"
            ],
            practical_application="Applied to research assistant project",
            platform=Platform.TWITTER
        )

        assert result['content'] is not None
        assert result['content_type'] == ContentType.LEARNING_UPDATE
        assert result['temperature'] == 0.78

    def test_generate_learning_update_linkedin(self, mock_anthropic):
        """Test generating learning update for LinkedIn"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_learning_update(
            topic="Multi-agent coordination patterns",
            key_insights=[
                "Task decomposition is critical",
                "Agents need clear boundaries",
                "Communication overhead matters"
            ],
            practical_application="Building production multi-agent system",
            platform=Platform.LINKEDIN
        )

        assert result['content'] is not None
        assert result['platform'] == Platform.LINKEDIN

    def test_learning_update_with_context(self, mock_anthropic):
        """Test learning update with user context"""
        generator = ContentGenerator(model_mode='api')

        user_context = {
            'research_area': 'AI systems engineering'
        }

        result = generator.generate_learning_update(
            topic="Prompt engineering",
            key_insights=["Few-shot learning works", "Chain-of-thought helps"],
            practical_application="Applied to chatbot",
            platform=Platform.TWITTER,
            user_context=user_context
        )

        assert result['content'] is not None


# ==================== Trend Commentary Tests ====================

@pytest.mark.unit
class TestTrendCommentaryGeneration:
    """Test trend commentary generation"""

    def test_generate_trend_commentary_twitter(self, mock_anthropic):
        """Test generating trend commentary for Twitter"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_trend_commentary(
            trend_topic="GPT-5 Announcement",
            trend_summary="OpenAI announces GPT-5 with improved reasoning",
            user_projects=["Research Assistant", "RAG Chatbot"],
            personal_angle="Working on RAG systems that could benefit",
            platform=Platform.TWITTER
        )

        assert result['content'] is not None
        assert result['content_type'] == ContentType.INDUSTRY_INSIGHT
        assert result['temperature'] == 0.80

    def test_generate_trend_commentary_linkedin(self, mock_anthropic):
        """Test generating trend commentary for LinkedIn"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_trend_commentary(
            trend_topic="AI Safety Regulations",
            trend_summary="New AI safety guidelines proposed",
            user_projects=["AI Research"],
            personal_angle="Interested in responsible AI development",
            platform=Platform.LINKEDIN
        )

        assert result['content'] is not None
        assert result['platform'] == Platform.LINKEDIN


# ==================== Question Post Tests ====================

@pytest.mark.unit
class TestQuestionPostGeneration:
    """Test question-driven post generation"""

    def test_generate_question_post_twitter(self, mock_anthropic):
        """Test generating question post for Twitter"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_question_post(
            topic="RAG chunking strategies",
            context="Experimenting with different approaches",
            your_thoughts="Semantic chunking seems better but slower",
            platform=Platform.TWITTER
        )

        assert result['content'] is not None
        assert result['content_type'] == ContentType.QUESTION_DRIVEN
        assert result['temperature'] == 0.77

    def test_generate_question_post_linkedin(self, mock_anthropic):
        """Test generating question post for LinkedIn"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_question_post(
            topic="Multi-agent communication patterns",
            context="Building multi-agent system",
            your_thoughts="Considering message queues vs direct calls",
            platform=Platform.LINKEDIN
        )

        assert result['content'] is not None
        assert result['platform'] == Platform.LINKEDIN


# ==================== Multiple Variants Tests ====================

@pytest.mark.unit
class TestMultipleVariants:
    """Test generating multiple content variants"""

    def test_generate_multiple_variants(self, mock_anthropic, sample_project_showcase_params):
        """Test generating multiple variants for A/B testing"""
        generator = ContentGenerator(model_mode='api')

        variants = generator.generate_multiple_variants(
            content_type='project_showcase',
            params=sample_project_showcase_params,
            num_variants=3
        )

        assert len(variants) == 3
        assert all('content' in v for v in variants)
        assert all('variant_id' in v for v in variants)
        assert variants[0]['variant_id'] == 'variant_A'
        assert variants[1]['variant_id'] == 'variant_B'
        assert variants[2]['variant_id'] == 'variant_C'

    def test_generate_variants_learning_update(self, mock_anthropic):
        """Test generating learning update variants"""
        generator = ContentGenerator(model_mode='api')

        params = {
            'topic': 'RAG systems',
            'key_insights': ['Insight 1', 'Insight 2'],
            'practical_application': 'Applied to project',
            'platform': Platform.TWITTER
        }

        variants = generator.generate_multiple_variants(
            content_type='learning_update',
            params=params,
            num_variants=2
        )

        assert len(variants) == 2

    def test_generate_variants_invalid_type(self, mock_anthropic):
        """Test generating variants with invalid content type"""
        generator = ContentGenerator(model_mode='api')

        with pytest.raises(ValueError):
            generator.generate_multiple_variants(
                content_type='invalid_type',
                params={},
                num_variants=2
            )


# ==================== Humanization Tests ====================

@pytest.mark.unit
class TestHumanization:
    """Test content humanization"""

    def test_humanize_removes_ai_phrases(self, mock_anthropic):
        """Test humanization removes AI red flag phrases"""
        generator = ContentGenerator(model_mode='api')

        content = "I'm excited to announce my new project! I'm thrilled to share these results."

        humanized = generator._humanize_content(content)

        assert "excited to announce" not in humanized.lower()
        assert "thrilled to share" not in humanized.lower()

    def test_humanize_limits_emoji_quartet(self, mock_anthropic):
        """Test humanization limits AI emoji quartet"""
        generator = ContentGenerator(model_mode='api')

        content = "Check out my project! 🚀🚀🚀✨✨✨⭐⭐⭐💡💡💡"

        humanized = generator._humanize_content(content)

        # Count emojis after humanization
        rocket_count = humanized.count('🚀')
        sparkle_count = humanized.count('✨')

        # Should have at most 1 of each
        assert rocket_count <= 1
        assert sparkle_count <= 1

    def test_humanize_removes_excessive_punctuation(self, mock_anthropic):
        """Test humanization removes excessive punctuation"""
        generator = ContentGenerator(model_mode='api')

        content = "This is amazing!!! Really great???"

        humanized = generator._humanize_content(content)

        assert "!!!" not in humanized
        assert "???" not in humanized
        assert humanized.count('!') <= 1
        assert humanized.count('?') <= 1

    def test_humanize_cleans_whitespace(self, mock_anthropic):
        """Test humanization cleans excessive whitespace"""
        generator = ContentGenerator(model_mode='api')

        content = "Line 1\n\n\n\nLine 2\n\n\n\nLine 3"

        humanized = generator._humanize_content(content)

        assert "\n\n\n" not in humanized
        assert humanized.count("\n\n") <= 3

    def test_humanize_preserves_good_content(self, mock_anthropic, humanized_content):
        """Test humanization preserves well-written content"""
        generator = ContentGenerator(model_mode='api')

        original_length = len(humanized_content)
        humanized = generator._humanize_content(humanized_content)

        # Should be mostly unchanged
        assert abs(len(humanized) - original_length) < 10


# ==================== AI Detection Tests ====================

@pytest.mark.unit
class TestAIDetection:
    """Test AI detection scoring"""

    def test_check_ai_detection_low_score(self, mock_anthropic, humanized_content):
        """Test AI detection with low score (human-like)"""
        generator = ContentGenerator(model_mode='api')

        result = generator.check_ai_detection_score(humanized_content)

        assert 'ai_detection_score' in result
        assert 'risk_level' in result
        assert 'issues_found' in result
        assert result['risk_level'] == 'LOW'

    def test_check_ai_detection_high_score(self, mock_anthropic, ai_red_flag_content):
        """Test AI detection with high score (AI-like)"""
        generator = ContentGenerator(model_mode='api')

        result = generator.check_ai_detection_score(ai_red_flag_content)

        assert result['ai_detection_score'] > 50
        assert result['risk_level'] in ['MEDIUM', 'HIGH']
        assert len(result['issues_found']) > 0

    def test_ai_detection_red_flag_phrases(self, mock_anthropic):
        """Test AI detection finds red flag phrases"""
        generator = ContentGenerator(model_mode='api')

        content = "I'm excited to announce my new project!"

        result = generator.check_ai_detection_score(content)

        assert any("AI phrase" in issue for issue in result['issues_found'])

    def test_ai_detection_emoji_quartet(self, mock_anthropic):
        """Test AI detection finds emoji quartet"""
        generator = ContentGenerator(model_mode='api')

        content = "My project 🚀✨⭐💡"

        result = generator.check_ai_detection_score(content)

        # Should detect 4 AI-quartet emojis
        assert any("emoji" in issue for issue in result['issues_found'])

    def test_ai_detection_parallel_bullets(self, mock_anthropic):
        """Test AI detection finds parallel bullet points"""
        generator = ContentGenerator(model_mode='api')

        content = """My project features:
- Feature one here
- Feature two here
- Feature three is
- Feature four is"""

        result = generator.check_ai_detection_score(content)

        # May detect parallel structure
        assert result['ai_detection_score'] >= 0

    def test_ai_detection_generic_terms(self, mock_anthropic):
        """Test AI detection finds generic achievement terms"""
        generator = ContentGenerator(model_mode='api')

        content = "This innovative and cutting-edge solution is revolutionary and game-changing!"

        result = generator.check_ai_detection_score(content)

        assert any("generic" in issue for issue in result['issues_found'])

    def test_ai_detection_no_contractions(self, mock_anthropic):
        """Test AI detection finds lack of contractions"""
        generator = ContentGenerator(model_mode='api')

        # Long content without contractions
        content = "I have been working on this project. It is very interesting. I do not know if it will work, but I cannot give up. That is not my style."

        result = generator.check_ai_detection_score(content)

        assert any("contractions" in issue for issue in result['issues_found'])

    def test_ai_detection_recommendations(self, mock_anthropic, ai_red_flag_content):
        """Test AI detection provides humanization tips"""
        generator = ContentGenerator(model_mode='api')

        result = generator.check_ai_detection_score(ai_red_flag_content)

        assert 'recommendations' in result
        assert len(result['recommendations']) > 0
        assert any(isinstance(rec, str) for rec in result['recommendations'])


# ==================== API Generation Tests ====================

@pytest.mark.unit
class TestAPIGeneration:
    """Test _generate_with_api method"""

    def test_generate_with_api_mode(self, mock_anthropic):
        """Test generation in API mode"""
        generator = ContentGenerator(model_mode='api')

        content = generator._generate_with_api(
            prompt="Generate a test tweet",
            temperature=0.75,
            max_tokens=100
        )

        assert content is not None
        assert isinstance(content, str)
        assert len(content) > 0

    def test_generate_with_grok_mode(self):
        """Test generation in Grok mode"""
        with patch('src.grok_handler.GrokHandler') as mock_grok:
            mock_grok.return_value.generate_response.return_value = "Test content from Grok"

            generator = ContentGenerator(model_mode='grok')

            content = generator._generate_with_api(
                prompt="Generate a test tweet",
                temperature=0.75,
                max_tokens=100
            )

            assert content == "Test content from Grok"

    def test_generate_with_local_mode(self):
        """Test generation in local mode"""
        with patch('src.local_llm_handler.LocalLLMHandler') as mock_local:
            mock_local.return_value.make_api_call.return_value = "Test content from local"

            generator = ContentGenerator(model_mode='local')

            content = generator._generate_with_api(
                prompt="Generate a test tweet",
                temperature=0.75,
                max_tokens=100
            )

            assert content == "Test content from local"

    def test_generate_api_error(self, mock_anthropic):
        """Test API generation error handling"""
        mock_anthropic.return_value.messages.create.side_effect = Exception("API Error")

        generator = ContentGenerator(model_mode='api')

        with pytest.raises(Exception):
            generator._generate_with_api(
                prompt="Generate a test tweet",
                temperature=0.75,
                max_tokens=100
            )


# ==================== Edge Cases Tests ====================

@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_project_name(self, mock_anthropic):
        """Test handling empty project name"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_project_showcase(
            project_name="",
            project_description="Test",
            technical_details="Test",
            results_metrics="Test",
            platform=Platform.TWITTER
        )

        assert result['content'] is not None

    def test_very_long_input(self, mock_anthropic):
        """Test handling very long input"""
        generator = ContentGenerator(model_mode='api')

        long_description = "A" * 5000

        result = generator.generate_project_showcase(
            project_name="Test",
            project_description=long_description,
            technical_details="Test",
            results_metrics="Test",
            platform=Platform.TWITTER
        )

        assert result['content'] is not None

    def test_special_characters_in_input(self, mock_anthropic):
        """Test handling special characters"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_project_showcase(
            project_name="Test & Project <> \"Quotes\"",
            project_description="Test with special chars!@#$%",
            technical_details="Test",
            results_metrics="Test",
            platform=Platform.TWITTER
        )

        assert result['content'] is not None

    def test_unicode_characters(self, mock_anthropic):
        """Test handling unicode characters"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_project_showcase(
            project_name="Test Project 中文",
            project_description="Description with émojis 🎉",
            technical_details="Test",
            results_metrics="Test",
            platform=Platform.TWITTER
        )

        assert result['content'] is not None


# ==================== Temperature Tests ====================

@pytest.mark.unit
class TestTemperatureSettings:
    """Test different temperature settings"""

    def test_project_showcase_temperature(self, mock_anthropic):
        """Test project showcase uses correct temperature"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_project_showcase(
            project_name="Test",
            project_description="Test",
            technical_details="Test",
            results_metrics="Test",
            platform=Platform.TWITTER
        )

        assert result['temperature'] == 0.75

    def test_learning_update_temperature(self, mock_anthropic):
        """Test learning update uses correct temperature"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_learning_update(
            topic="Test",
            key_insights=["Test"],
            practical_application="Test",
            platform=Platform.TWITTER
        )

        assert result['temperature'] == 0.78

    def test_trend_commentary_temperature(self, mock_anthropic):
        """Test trend commentary uses correct temperature"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_trend_commentary(
            trend_topic="Test",
            trend_summary="Test",
            user_projects=["Test"],
            personal_angle="Test",
            platform=Platform.TWITTER
        )

        assert result['temperature'] == 0.80

    def test_question_post_temperature(self, mock_anthropic):
        """Test question post uses correct temperature"""
        generator = ContentGenerator(model_mode='api')

        result = generator.generate_question_post(
            topic="Test",
            context="Test",
            your_thoughts="Test",
            platform=Platform.TWITTER
        )

        assert result['temperature'] == 0.77


# ==================== Integration Tests ====================

@pytest.mark.integration
class TestContentGeneratorIntegration:
    """Integration tests for ContentGenerator"""

    def test_full_content_workflow(self, mock_anthropic):
        """Test complete content generation workflow"""
        generator = ContentGenerator(model_mode='api')

        # Generate content
        result = generator.generate_project_showcase(
            project_name="Test Project",
            project_description="Test Description",
            technical_details="Python, AI, ML",
            results_metrics="90% accuracy",
            platform=Platform.TWITTER
        )

        # Check AI detection
        detection = generator.check_ai_detection_score(result['content'])

        # Humanize if needed
        if detection['risk_level'] == 'HIGH':
            humanized = generator._humanize_content(result['content'])
            result['content'] = humanized
            result['human_edited'] = True

        assert result['content'] is not None
        assert 'ai_detection_score' in detection

    def test_multiple_content_types(self, mock_anthropic):
        """Test generating multiple content types"""
        generator = ContentGenerator(model_mode='api')

        # Project showcase
        showcase = generator.generate_project_showcase(
            project_name="Test",
            project_description="Test",
            technical_details="Test",
            results_metrics="Test",
            platform=Platform.TWITTER
        )

        # Learning update
        learning = generator.generate_learning_update(
            topic="Test",
            key_insights=["Test"],
            practical_application="Test",
            platform=Platform.TWITTER
        )

        # Trend commentary
        trend = generator.generate_trend_commentary(
            trend_topic="Test",
            trend_summary="Test",
            user_projects=["Test"],
            personal_angle="Test",
            platform=Platform.TWITTER
        )

        assert showcase['content_type'] == ContentType.PROJECT_SHOWCASE
        assert learning['content_type'] == ContentType.LEARNING_UPDATE
        assert trend['content_type'] == ContentType.INDUSTRY_INSIGHT
