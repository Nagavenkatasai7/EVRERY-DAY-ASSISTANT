"""
Integration tests for Resume Maker with new model routing
Tests end-to-end functionality of Resume Generator and Job Analyzer with different models
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.generators.resume_generator import ResumeGenerator
from src.analyzers.job_analyzer import JobAnalyzer


class TestResumeGeneratorIntegration:
    """Integration tests for ResumeGenerator with model routing"""

    def test_resume_generator_with_claude(self):
        """Test ResumeGenerator works with Claude API"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                # Mock the API response
                mock_message = Mock()
                mock_content = Mock()
                mock_content.text = "# John Doe\nSoftware Engineer Resume..."
                mock_message.content = [mock_content]

                mock_client = Mock()
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                generator = ResumeGenerator(model_mode='api')

                profile_text = "John Doe, Software Engineer with 5 years experience"
                job_analysis = {
                    'company_name': 'Google',
                    'job_title': 'Senior Software Engineer',
                    'required_skills': ['Python', 'Java'],
                    'keywords': ['Python', 'Java', 'AWS']
                }

                result = generator.generate_resume(profile_text, job_analysis)

                assert result['success'] is True
                assert 'John Doe' in result['content']
                mock_client.messages.create.assert_called_once()

    def test_resume_generator_with_grok(self):
        """Test ResumeGenerator works with Grok API"""
        with patch.dict(os.environ, {'MODEL_MODE': 'grok', 'GROK_API_KEY': 'test_key',
                                     'GROK_MAX_TOKENS': '8192', 'GROK_TEMPERATURE': '0.7'}):
            with patch('src.grok_handler.GrokHandler') as mock_grok_class:
                mock_grok = Mock()
                mock_grok.generate_response.return_value = "# Jane Smith\nData Scientist Resume..."
                mock_grok_class.return_value = mock_grok

                generator = ResumeGenerator(model_mode='grok')

                profile_text = "Jane Smith, Data Scientist"
                job_analysis = {
                    'company_name': 'Microsoft',
                    'job_title': 'Senior Data Scientist',
                    'required_skills': ['Python', 'ML'],
                    'keywords': ['Python', 'ML', 'TensorFlow']
                }

                result = generator.generate_resume(profile_text, job_analysis)

                assert result['success'] is True
                assert 'Jane Smith' in result['content']
                mock_grok.generate_response.assert_called_once()

    def test_resume_generator_with_local_llm(self):
        """Test ResumeGenerator works with Local LLM"""
        with patch.dict(os.environ, {'MODEL_MODE': 'local', 'LOCAL_MODEL_NAME': 'llama3.1:latest'}):
            with patch('src.local_llm_handler.LocalLLMHandler') as mock_local_class:
                mock_local = Mock()
                mock_local.make_api_call.return_value = "# Bob Johnson\nEngineer Resume..."
                mock_local.model_name = "llama3.1:latest"
                mock_local_class.return_value = mock_local

                generator = ResumeGenerator(model_mode='local')

                profile_text = "Bob Johnson, Engineer"
                job_analysis = {
                    'company_name': 'Amazon',
                    'job_title': 'DevOps Engineer',
                    'required_skills': ['Docker', 'Kubernetes'],
                    'keywords': ['Docker', 'Kubernetes', 'AWS']
                }

                result = generator.generate_resume(profile_text, job_analysis)

                assert result['success'] is True
                assert 'Bob Johnson' in result['content']
                mock_local.make_api_call.assert_called_once()

    def test_resume_generator_error_handling(self):
        """Test that ResumeGenerator handles API errors gracefully"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = Mock()
                mock_client.messages.create.side_effect = Exception("API Error")
                mock_anthropic.return_value = mock_client

                generator = ResumeGenerator(model_mode='api')

                profile_text = "Test User"
                job_analysis = {'company_name': 'TestCorp', 'job_title': 'Engineer'}

                result = generator.generate_resume(profile_text, job_analysis)

                assert result['success'] is False
                assert 'error' in result


class TestJobAnalyzerIntegration:
    """Integration tests for JobAnalyzer with model routing"""

    def test_job_analyzer_with_claude(self):
        """Test JobAnalyzer works with Claude API"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                # Mock the API response
                mock_message = Mock()
                mock_content = Mock()
                mock_content.text = '''{
                    "company_name": "Google",
                    "job_title": "Software Engineer",
                    "required_skills": ["Python", "Java"],
                    "preferred_skills": ["AWS", "Docker"],
                    "keywords": ["Python", "Java", "AWS", "Docker"],
                    "years_of_experience": "3-5 years",
                    "education_requirements": "Bachelor's in CS",
                    "key_responsibilities": ["Develop software", "Write tests"],
                    "industry": "Technology",
                    "role_type": "Software Engineer"
                }'''
                mock_message.content = [mock_content]

                mock_client = Mock()
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                analyzer = JobAnalyzer(model_mode='api')

                job_description = "We are hiring a Software Engineer with Python and Java experience..."
                result = analyzer.analyze_job_description(job_description, "Google")

                assert result['company_name'] == 'Google'
                assert result['job_title'] == 'Software Engineer'
                assert 'Python' in result['required_skills']
                mock_client.messages.create.assert_called_once()

    def test_job_analyzer_with_grok(self):
        """Test JobAnalyzer works with Grok API"""
        with patch.dict(os.environ, {'MODEL_MODE': 'grok', 'GROK_API_KEY': 'test_key',
                                     'GROK_MAX_TOKENS': '8192', 'GROK_TEMPERATURE': '0.7'}):
            with patch('src.grok_handler.GrokHandler') as mock_grok_class:
                mock_grok = Mock()
                mock_grok.generate_response.return_value = '''{
                    "company_name": "Microsoft",
                    "job_title": "Data Scientist",
                    "required_skills": ["Python", "ML"],
                    "preferred_skills": ["TensorFlow"],
                    "keywords": ["Python", "ML", "TensorFlow"],
                    "years_of_experience": "5+ years",
                    "education_requirements": "MS in Data Science",
                    "key_responsibilities": ["Build ML models"],
                    "industry": "Technology",
                    "role_type": "Data Scientist"
                }'''
                mock_grok_class.return_value = mock_grok

                analyzer = JobAnalyzer(model_mode='grok')

                job_description = "Looking for a Data Scientist with Python and ML expertise..."
                result = analyzer.analyze_job_description(job_description, "Microsoft")

                assert result['company_name'] == 'Microsoft'
                assert result['job_title'] == 'Data Scientist'
                assert 'Python' in result['required_skills']
                mock_grok.generate_response.assert_called_once()

    def test_job_analyzer_json_extraction(self):
        """Test that JobAnalyzer properly extracts JSON from markdown code blocks"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                # Mock response with markdown code block
                mock_message = Mock()
                mock_content = Mock()
                mock_content.text = '''```json
{
    "company_name": "Amazon",
    "job_title": "DevOps Engineer",
    "required_skills": ["Docker", "Kubernetes"],
    "preferred_skills": ["AWS"],
    "keywords": ["Docker", "Kubernetes", "AWS"],
    "years_of_experience": "2-4 years",
    "education_requirements": "Bachelor's degree",
    "key_responsibilities": ["Manage infrastructure"],
    "industry": "Technology",
    "role_type": "DevOps Engineer"
}
```'''
                mock_message.content = [mock_content]

                mock_client = Mock()
                mock_client.messages.create.return_value = mock_message
                mock_anthropic.return_value = mock_client

                analyzer = JobAnalyzer(model_mode='api')

                job_description = "DevOps Engineer needed..."
                result = analyzer.analyze_job_description(job_description, "Amazon")

                assert result['company_name'] == 'Amazon'
                assert result['job_title'] == 'DevOps Engineer'
                assert 'Docker' in result['required_skills']

    def test_job_analyzer_error_handling(self):
        """Test that JobAnalyzer handles API errors gracefully"""
        with patch.dict(os.environ, {'MODEL_MODE': 'api', 'ANTHROPIC_API_KEY': 'test_key'}):
            with patch('anthropic.Anthropic') as mock_anthropic:
                mock_client = Mock()
                mock_client.messages.create.side_effect = Exception("API Error")
                mock_anthropic.return_value = mock_client

                analyzer = JobAnalyzer(model_mode='api')

                job_description = "Test job description"
                result = analyzer.analyze_job_description(job_description, "TestCorp")

                # Should return fallback response
                assert result['company_name'] == 'TestCorp'
                assert 'error' in result


class TestEndToEndIntegration:
    """End-to-end integration tests for complete resume generation workflow"""

    def test_complete_resume_workflow_with_research(self):
        """Test complete workflow: job analysis -> company research -> resume generation"""
        with patch.dict(os.environ, {
            'MODEL_MODE': 'api',
            'ANTHROPIC_API_KEY': 'test_key',
            'TAVILY_API_KEY': 'test_tavily_key'
        }):
            with patch('anthropic.Anthropic') as mock_anthropic:
                with patch('src.resume_utils.research_router.WebSearchClient', create=True) as mock_tavily_class:
                    # Mock Claude API
                    mock_message1 = Mock()
                    mock_content1 = Mock()
                    mock_content1.text = '''{
                        "company_name": "Google",
                        "job_title": "Software Engineer",
                        "required_skills": ["Python", "Java"],
                        "keywords": ["Python", "Java", "AWS"]
                    }'''
                    mock_message1.content = [mock_content1]

                    mock_message2 = Mock()
                    mock_content2 = Mock()
                    mock_content2.text = "# John Doe\nSoftware Engineer Resume..."
                    mock_message2.content = [mock_content2]

                    mock_client = Mock()
                    mock_client.messages.create.side_effect = [mock_message1, mock_message2]
                    mock_anthropic.return_value = mock_client

                    # Mock Tavily
                    mock_tavily = Mock()
                    mock_tavily.search.return_value = [
                        {'title': 'About Google', 'content': 'Google is...', 'url': 'http://google.com'}
                    ]
                    mock_tavily_class.return_value = mock_tavily

                    # Run workflow
                    from src.resume_utils.research_router import ResearchRouter

                    analyzer = JobAnalyzer(model_mode='api')
                    router = ResearchRouter(research_api='tavily')
                    generator = ResumeGenerator(model_mode='api')

                    # Step 1: Analyze job
                    job_analysis = analyzer.analyze_job_description(
                        "Software Engineer position at Google...",
                        "Google"
                    )

                    # Step 2: Research company
                    company_research = router.research_company(
                        job_analysis['company_name'],
                        job_analysis['job_title']
                    )

                    # Step 3: Generate resume
                    profile_text = "John Doe, experienced software engineer"
                    result = generator.generate_resume(
                        profile_text,
                        job_analysis,
                        company_research
                    )

                    # Verify results
                    assert job_analysis['company_name'] == 'Google'
                    assert company_research is not None
                    assert company_research['source'] == 'Tavily Search'
                    assert result['success'] is True
                    assert 'John Doe' in result['content']


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
