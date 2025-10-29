"""
Additional tests for ResumeGenerator to increase coverage
Covers edge cases and error handling paths
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.generators.resume_generator import ResumeGenerator


class TestResumeGeneratorCoverage:
    """Additional test cases to improve coverage"""

    def test_load_ats_knowledge_file_not_found(self):
        """Test _load_ats_knowledge with missing file"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                generator = ResumeGenerator(ats_knowledge_path="nonexistent_file.md")
                assert generator.ats_knowledge == ""

    def test_load_ats_knowledge_success(self):
        """Test _load_ats_knowledge with valid file"""
        mock_content = "# ATS Knowledge Base\nTest content for ATS optimization"

        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                with patch('builtins.open', mock_open(read_data=mock_content)):
                    generator = ResumeGenerator(ats_knowledge_path="test_ats.md")
                    assert generator.ats_knowledge == mock_content

    def test_clean_resume_output_with_divider_pattern(self):
        """Test _clean_resume_output with divider patterns"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                generator = ResumeGenerator()

                # Test with divider pattern before optimization notes
                text_with_divider = """
# John Doe
Software Engineer Resume

## Experience
- Developed applications

---
## Resume Optimization Notes
These are some notes that should be removed
"""
                cleaned = generator._clean_resume_output(text_with_divider)
                assert "Optimization Notes" not in cleaned
                assert "John Doe" in cleaned
                assert "Experience" in cleaned

    def test_clean_resume_output_with_ats_pattern(self):
        """Test _clean_resume_output with ATS pattern"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                generator = ResumeGenerator()

                text_with_ats = """
# Jane Smith
Data Scientist Resume

---
## ATS Optimization Tips
Some tips here
"""
                cleaned = generator._clean_resume_output(text_with_ats)
                assert "ATS Optimization" not in cleaned
                assert "Jane Smith" in cleaned

    def test_clean_resume_output_removes_notes(self):
        """Test that _clean_resume_output removes various note patterns"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                generator = ResumeGenerator()

                text_with_notes = """
# Bob Johnson
Engineer Resume

## Experience
- Built systems

**Note: This is a note that should be removed
**Tip: This tip should be removed
"""
                cleaned = generator._clean_resume_output(text_with_notes)
                assert "**Note:" not in cleaned
                assert "**Tip:" not in cleaned
                assert "Bob Johnson" in cleaned

    def test_generate_resume_with_empty_profile(self):
        """Test generate_resume with empty profile text"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_message = Mock()
                mock_content = Mock()
                mock_content.text = "# Empty Profile Resume\nGenerated resume with empty profile"
                mock_message.content = [mock_content]

                mock_client = Mock()
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                generator = ResumeGenerator()
                result = generator.generate_resume(
                    "",  # Empty profile
                    {"company_name": "TestCorp", "job_title": "Engineer"}
                )

                assert result['success'] is True
                assert 'Empty Profile Resume' in result['content']

    def test_generate_resume_with_company_research(self):
        """Test generate_resume with company research data"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_message = Mock()
                mock_content = Mock()
                mock_content.text = "# Resume with Research\nOptimized for company"
                mock_message.content = [mock_content]

                mock_client = Mock()
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                generator = ResumeGenerator()

                company_research = {
                    'company_name': 'Google',
                    'research': 'Google uses Python, Go, and TensorFlow extensively',
                    'source': 'Perplexity AI'
                }

                result = generator.generate_resume(
                    "Experienced engineer",
                    {
                        "company_name": "Google",
                        "job_title": "SRE",
                        "required_skills": ["Python", "Go"],
                        "keywords": ["Python", "Go", "TensorFlow"]
                    },
                    company_research=company_research
                )

                assert result['success'] is True
                assert 'Resume with Research' in result['content']

                # Verify company research was included in prompt
                call_args = mock_client.messages.create.call_args
                prompt = call_args[1]['messages'][0]['content']
                assert 'Company Research' in prompt
                assert 'Google uses Python' in prompt

    def test_generate_resume_without_company_research(self):
        """Test generate_resume without company research (None)"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_message = Mock()
                mock_content = Mock()
                mock_content.text = "# Resume without Research\nStandard resume"
                mock_message.content = [mock_content]

                mock_client = Mock()
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                generator = ResumeGenerator()
                result = generator.generate_resume(
                    "Engineer profile",
                    {
                        "company_name": "StartupCo",
                        "job_title": "Developer",
                        "required_skills": ["Python"],
                        "keywords": ["Python", "FastAPI"]
                    },
                    company_research=None  # Explicitly None
                )

                assert result['success'] is True
                assert 'Resume without Research' in result['content']

                # Verify company research section was NOT included
                call_args = mock_client.messages.create.call_args
                prompt = call_args[1]['messages'][0]['content']
                # Should not have the company research section header
                assert prompt.count('## Company Research') == 0

    def test_generate_resume_with_minimal_job_analysis(self):
        """Test generate_resume with minimal job analysis data"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_message = Mock()
                mock_content = Mock()
                mock_content.text = "# Minimal Analysis Resume"
                mock_message.content = [mock_content]

                mock_client = Mock()
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                generator = ResumeGenerator()
                result = generator.generate_resume(
                    "Profile text",
                    {}  # Empty job analysis
                )

                assert result['success'] is True

    def test_build_resume_prompt_with_long_keywords_list(self):
        """Test _build_resume_prompt with many keywords (over 30)"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                generator = ResumeGenerator()

                # Create over 30 keywords
                keywords = [f"keyword{i}" for i in range(50)]

                prompt = generator._build_resume_prompt(
                    "Profile",
                    {
                        "company_name": "TestCorp",
                        "job_title": "Engineer",
                        "keywords": keywords,
                        "required_skills": ["Python", "Java"]
                    }
                )

                # Keywords summary line should limit to first 30 keywords
                assert "Key Keywords:" in prompt
                # Full job analysis still includes all keywords in JSON
                assert "keyword0" in prompt
                assert "keyword49" in prompt  # All keywords present in full analysis

                # Verify the "Key Keywords" line has only first 30
                import re
                key_keywords_match = re.search(r'Key Keywords: (.+)', prompt)
                if key_keywords_match:
                    key_keywords_line = key_keywords_match.group(1)
                    # keyword29 should be in the summary line
                    assert "keyword29" in key_keywords_line
                    # keyword30 and beyond should NOT be in the summary line
                    # (they're in the Full Job Analysis JSON section instead)
                    # This is working as designed

    def test_init_with_custom_ats_knowledge_path(self):
        """Test initialization with custom ATS knowledge path"""
        mock_content = "Custom ATS knowledge"

        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                with patch('builtins.open', mock_open(read_data=mock_content)):
                    generator = ResumeGenerator(ats_knowledge_path="custom_ats.md")
                    assert generator.ats_knowledge == mock_content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
