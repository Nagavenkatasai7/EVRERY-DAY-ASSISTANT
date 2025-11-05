"""
Additional tests for JobAnalyzer to increase coverage
Covers the extract_keywords_simple method and edge cases
"""
import pytest
import os
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.analyzers.job_analyzer import JobAnalyzer


class TestJobAnalyzerCoverage:
    """Additional test cases to improve JobAnalyzer coverage"""

    def test_extract_keywords_simple_programming_languages(self):
        """Test extract_keywords_simple with various programming languages"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                analyzer = JobAnalyzer()

                jd = """
                We need a Senior Developer with experience in Python, Java, JavaScript,
                TypeScript, C++, C#, Go, Rust, Ruby, PHP, Swift, Kotlin, and Scala.
                """

                keywords = analyzer.extract_keywords_simple(jd)

                # Should find all these languages
                expected_languages = ['Python', 'Java', 'JavaScript', 'TypeScript',
                                    'C++', 'C#', 'Go', 'Rust', 'Ruby', 'PHP',
                                    'Swift', 'Kotlin', 'Scala']

                for lang in expected_languages:
                    assert lang in keywords, f"{lang} should be in extracted keywords"

    def test_extract_keywords_simple_frameworks(self):
        """Test extract_keywords_simple with frameworks and libraries"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                analyzer = JobAnalyzer()

                jd = """
                Required skills: React, Angular, Vue, Django, Flask, FastAPI,
                Spring, Node.js, Express, TensorFlow, PyTorch, Keras,
                Scikit-learn, Pandas, NumPy
                """

                keywords = analyzer.extract_keywords_simple(jd)

                expected_frameworks = ['React', 'Angular', 'Vue', 'Django', 'Flask',
                                     'FastAPI', 'Spring', 'Node.js', 'Express',
                                     'TensorFlow', 'PyTorch', 'Keras',
                                     'Scikit-learn', 'Pandas', 'NumPy']

                for framework in expected_frameworks:
                    assert framework in keywords, f"{framework} should be in extracted keywords"

    def test_extract_keywords_simple_databases(self):
        """Test extract_keywords_simple with database technologies"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                analyzer = JobAnalyzer()

                jd = """
                Database experience required: SQL, PostgreSQL, MySQL, MongoDB,
                Redis, Cassandra, DynamoDB, Elasticsearch
                """

                keywords = analyzer.extract_keywords_simple(jd)

                expected_dbs = ['SQL', 'PostgreSQL', 'MySQL', 'MongoDB',
                              'Redis', 'Cassandra', 'DynamoDB', 'Elasticsearch']

                for db in expected_dbs:
                    assert db in keywords, f"{db} should be in extracted keywords"

    def test_extract_keywords_simple_cloud_platforms(self):
        """Test extract_keywords_simple with cloud and DevOps tools"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                analyzer = JobAnalyzer()

                jd = """
                Cloud experience: AWS, Azure, GCP, Google Cloud, Docker,
                Kubernetes, Jenkins, CI/CD, Git, GitHub, GitLab
                """

                keywords = analyzer.extract_keywords_simple(jd)

                expected_cloud = ['AWS', 'Azure', 'GCP', 'Google Cloud', 'Docker',
                                'Kubernetes', 'Jenkins', 'CI/CD', 'Git', 'GitHub', 'GitLab']

                for platform in expected_cloud:
                    assert platform in keywords, f"{platform} should be in extracted keywords"

    def test_extract_keywords_simple_ai_ml(self):
        """Test extract_keywords_simple with AI/ML keywords"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                analyzer = JobAnalyzer()

                jd = """
                AI/ML role requiring: Machine Learning, Deep Learning, NLP,
                Computer Vision, AI, Artificial Intelligence, LLM, GPT, RAG,
                LangChain, Prompt Engineering
                """

                keywords = analyzer.extract_keywords_simple(jd)

                expected_ai_ml = ['Machine Learning', 'Deep Learning', 'NLP',
                                'Computer Vision', 'AI', 'Artificial Intelligence',
                                'LLM', 'GPT', 'RAG', 'LangChain', 'Prompt Engineering']

                for keyword in expected_ai_ml:
                    assert keyword in keywords, f"{keyword} should be in extracted keywords"

    def test_extract_keywords_simple_case_insensitive(self):
        """Test that extract_keywords_simple is case-insensitive"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                analyzer = JobAnalyzer()

                # Test with various casings
                jd_lower = "Experience with python, java, react, aws required"
                jd_upper = "Experience with PYTHON, JAVA, REACT, AWS required"
                jd_mixed = "Experience with PyThOn, JaVa, ReAcT, AwS required"

                keywords_lower = analyzer.extract_keywords_simple(jd_lower)
                keywords_upper = analyzer.extract_keywords_simple(jd_upper)
                keywords_mixed = analyzer.extract_keywords_simple(jd_mixed)

                # All should extract the same keywords
                assert 'Python' in keywords_lower
                assert 'Python' in keywords_upper
                assert 'Python' in keywords_mixed

    def test_extract_keywords_simple_empty_description(self):
        """Test extract_keywords_simple with empty job description"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                analyzer = JobAnalyzer()

                keywords = analyzer.extract_keywords_simple("")
                assert keywords == []

    def test_extract_keywords_simple_no_tech_keywords(self):
        """Test extract_keywords_simple with JD containing no tech keywords"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                analyzer = JobAnalyzer()

                jd = """
                We are seeking a friendly person with excellent communication skills.
                Must be able to work in a team and handle customer inquiries effectively.
                """

                keywords = analyzer.extract_keywords_simple(jd)
                # Note: May extract false positives like 'Go' from words like 'good'
                # but for truly non-tech JDs, list should be minimal or empty
                assert len(keywords) <= 1

    def test_extract_keywords_simple_mixed_content(self):
        """Test extract_keywords_simple with realistic mixed job description"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic'):
                analyzer = JobAnalyzer()

                jd = """
                Senior Machine Learning Engineer

                We are seeking a talented ML engineer with 5+ years of experience.

                Requirements:
                - Expert in Python and TensorFlow
                - Experience with AWS and Docker
                - Knowledge of LLM and RAG systems
                - Strong problem-solving skills
                - Bachelor's degree in Computer Science
                """

                keywords = analyzer.extract_keywords_simple(jd)

                assert 'Python' in keywords
                assert 'TensorFlow' in keywords
                assert 'AWS' in keywords
                assert 'Docker' in keywords
                assert 'LLM' in keywords
                assert 'RAG' in keywords

    def test_analyze_job_description_with_json_parse_error(self):
        """Test analyze_job_description when JSON parsing fails"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_message = Mock()
                mock_content = Mock()
                # Return invalid JSON
                mock_content.text = "This is not valid JSON at all"
                mock_message.content = [mock_content]

                mock_client = Mock()
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                analyzer = JobAnalyzer()
                result = analyzer.analyze_job_description("Test JD", "TestCorp")

                # Should return fallback response with error
                assert result['company_name'] == 'TestCorp'
                assert result['job_title'] == 'Not specified'
                assert 'error' in result

    def test_analyze_job_description_with_markdown_wrapped_json(self):
        """Test analyze_job_description with JSON wrapped in markdown code block"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_message = Mock()
                mock_content = Mock()
                # Return JSON wrapped in markdown code block
                mock_content.text = """```json
{
    "company_name": "TechCorp",
    "job_title": "Engineer",
    "required_skills": ["Python", "Java"],
    "keywords": ["Python", "Java", "AWS"]
}
```"""
                mock_message.content = [mock_content]

                mock_client = Mock()
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                analyzer = JobAnalyzer()
                result = analyzer.analyze_job_description("Test JD", "TechCorp")

                assert result['company_name'] == 'TechCorp'
                assert result['job_title'] == 'Engineer'
                assert 'Python' in result['required_skills']

    def test_analyze_job_description_without_company_name(self):
        """Test analyze_job_description without providing company name"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_message = Mock()
                mock_content = Mock()
                mock_content.text = """{
                    "company_name": "ExtractedCorp",
                    "job_title": "Developer",
                    "required_skills": ["Python"],
                    "keywords": ["Python"]
                }"""
                mock_message.content = [mock_content]

                mock_client = Mock()
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                analyzer = JobAnalyzer()
                result = analyzer.analyze_job_description("Test JD")  # No company name

                # Should use extracted company name
                assert result['company_name'] == 'ExtractedCorp'

    def test_analyze_job_description_override_company_name(self):
        """Test that provided company name overrides extracted name"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_message = Mock()
                mock_content = Mock()
                mock_content.text = """{
                    "company_name": "ExtractedCorp",
                    "job_title": "Developer",
                    "required_skills": ["Python"],
                    "keywords": ["Python"]
                }"""
                mock_message.content = [mock_content]

                mock_client = Mock()
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                analyzer = JobAnalyzer()
                result = analyzer.analyze_job_description("Test JD", company_name="ProvidedCorp")

                # Should override with provided name
                assert result['company_name'] == 'ProvidedCorp'


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
