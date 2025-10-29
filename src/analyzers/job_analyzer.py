"""
Job description analyzer to extract company name, keywords, and requirements
"""
import re
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.resume_utils.model_client import UniversalModelClient

load_dotenv()

class JobAnalyzer:
    def __init__(self, model_mode=None):
        """
        Initialize job analyzer

        Args:
            model_mode: 'api' (Claude), 'grok' (xAI), 'local' (Ollama), or None (auto-detect)
        """
        self.client = UniversalModelClient(model_mode=model_mode)

    def analyze_job_description(self, job_description, company_name=None):
        """
        Analyze job description to extract key information
        Returns: dict with company_name, job_title, keywords, requirements, etc.
        """
        prompt = f"""Analyze this job description and extract key information in a structured JSON format.

Job Description:
{job_description}

{f"Company Name (if not in JD): {company_name}" if company_name else ""}

Please extract and return a JSON object with the following fields:
1. "company_name": The company name (extract from JD or use provided name)
2. "job_title": The job title/position
3. "required_skills": List of technical skills required
4. "preferred_skills": List of preferred/nice-to-have skills
5. "years_of_experience": Number of years required (if specified)
6. "education_requirements": Education requirements
7. "key_responsibilities": List of main responsibilities
8. "keywords": List of important keywords that should appear in the resume (extract from the entire JD - technical terms, tools, frameworks, methodologies, soft skills, etc.)
9. "industry": Industry/domain (if identifiable)
10. "role_type": Type of role (e.g., "Software Engineer", "Data Scientist", etc.)

Return ONLY the JSON object, no additional text.
"""

        try:
            response_text = self.client.generate(
                prompt=prompt,
                max_tokens=4000,
                temperature=0.7
            ).strip()

            # Try to extract JSON if wrapped in markdown code blocks
            if response_text.startswith("```"):
                response_text = re.sub(r'^```(?:json)?\s*|\s*```$', '', response_text, flags=re.MULTILINE).strip()

            analysis = json.loads(response_text)

            # Override company name if provided
            if company_name:
                analysis["company_name"] = company_name

            return analysis

        except Exception as e:
            print(f"Error analyzing job description: {e}")
            return {
                "company_name": company_name or "Unknown",
                "job_title": "Not specified",
                "required_skills": [],
                "preferred_skills": [],
                "keywords": [],
                "error": str(e)
            }

    def extract_keywords_simple(self, job_description):
        """
        Simple keyword extraction without API call (fallback method)
        """
        # Common technical keywords and patterns
        tech_keywords = set()

        # Programming languages
        languages = ['Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'C#', 'Go', 'Rust', 'Ruby', 'PHP', 'Swift', 'Kotlin', 'Scala']
        for lang in languages:
            if lang.lower() in job_description.lower():
                tech_keywords.add(lang)

        # Frameworks and libraries
        frameworks = ['React', 'Angular', 'Vue', 'Django', 'Flask', 'FastAPI', 'Spring', 'Node.js', 'Express', 'TensorFlow', 'PyTorch', 'Keras', 'Scikit-learn', 'Pandas', 'NumPy']
        for framework in frameworks:
            if framework.lower() in job_description.lower():
                tech_keywords.add(framework)

        # Databases
        databases = ['SQL', 'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Cassandra', 'DynamoDB', 'Elasticsearch']
        for db in databases:
            if db.lower() in job_description.lower():
                tech_keywords.add(db)

        # Cloud platforms
        cloud = ['AWS', 'Azure', 'GCP', 'Google Cloud', 'Docker', 'Kubernetes', 'Jenkins', 'CI/CD', 'Git', 'GitHub', 'GitLab']
        for platform in cloud:
            if platform.lower() in job_description.lower():
                tech_keywords.add(platform)

        # AI/ML keywords
        ai_ml = ['Machine Learning', 'Deep Learning', 'NLP', 'Computer Vision', 'AI', 'Artificial Intelligence', 'LLM', 'GPT', 'RAG', 'LangChain', 'Prompt Engineering']
        for keyword in ai_ml:
            if keyword.lower() in job_description.lower():
                tech_keywords.add(keyword)

        return list(tech_keywords)

def main():
    """Test the job analyzer"""
    sample_jd = """
    Senior Software Engineer - AI/ML Platform

    We are seeking a Senior Software Engineer to join our AI/ML Platform team.

    Requirements:
    - 5+ years of software engineering experience
    - Strong proficiency in Python and experience with machine learning frameworks (TensorFlow, PyTorch)
    - Experience with LLM integration and RAG systems
    - Proficiency with cloud platforms (AWS, GCP)
    - Experience with Docker, Kubernetes
    - Strong understanding of API design and microservices

    Nice to have:
    - Experience with LangChain, prompt engineering
    - Knowledge of vector databases (Pinecone, Weaviate)
    - React/TypeScript for frontend
    """

    analyzer = JobAnalyzer()
    result = analyzer.analyze_job_description(sample_jd, company_name="TechCorp")

    print("✓ Job Analysis Complete")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
