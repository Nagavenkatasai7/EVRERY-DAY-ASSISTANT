"""
AI-Powered ATS Resume Generator
Generates ATS-optimized resumes from profile PDF and job descriptions
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import anthropic
import PyPDF2

from config.settings import ANTHROPIC_API_KEY, MODEL_MODE, TAVILY_API_KEY
from utils.logger import get_logger

logger = get_logger(__name__)


class ResumeMaker:
    """
    AI-powered ATS resume generator

    Features:
    - Parses profile PDF to extract candidate information
    - Generates tailored resumes for specific job descriptions
    - ATS optimization with target score
    - Company research via Perplexity
    - Job analysis and matching
    """

    def __init__(self, model_mode: str = None, perplexity_key: str = None):
        """Initialize resume maker

        Args:
            model_mode: "api", "grok", or "local"
            perplexity_key: Optional Perplexity API key for company research
        """
        self.model_mode = model_mode or MODEL_MODE
        self.perplexity_key = perplexity_key

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

        logger.info(f"Resume maker initialized in {self.model_mode} mode")

    def parse_profile_pdf(self, pdf_path: str) -> Dict:
        """Parse profile PDF and extract candidate information

        Args:
            pdf_path: Path to profile PDF file

        Returns:
            Dict with extracted profile data: {
                'text': str,
                'name': str,
                'email': str,
                'phone': str,
                'summary': str,
                'experience': List[Dict],
                'education': List[Dict],
                'skills': List[str]
            }
        """
        try:
            # Extract text from PDF
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text()

            logger.info(f"Extracted {len(text)} characters from profile PDF")

            # Use AI to parse structured information
            prompt = f"""Parse this resume/profile and extract structured information:

{text}

Return as JSON with this structure:
{{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "phone number",
    "location": "city, state",
    "linkedin": "linkedin url if present",
    "summary": "professional summary",
    "experience": [
        {{
            "title": "Job Title",
            "company": "Company Name",
            "duration": "Start - End",
            "responsibilities": ["bullet 1", "bullet 2"]
        }}
    ],
    "education": [
        {{
            "degree": "Degree Name",
            "institution": "School Name",
            "year": "Graduation Year"
        }}
    ],
    "skills": ["skill1", "skill2", "skill3"],
    "certifications": ["cert1", "cert2"]
}}

Extract ALL information available. Return ONLY valid JSON."""

            if self.model_mode == "api":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text.strip()
            elif self.model_mode == "grok":
                result_text = self.grok_handler.generate_content(prompt, max_tokens=4000)
            else:  # local
                result_text = self.local_handler.generate_text(prompt, max_tokens=4000)

            # Extract JSON from response
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start != -1 and end > start:
                profile_data = json.loads(result_text[start:end])
                profile_data['raw_text'] = text
                return profile_data
            else:
                # Fallback if parsing fails
                return {
                    'raw_text': text,
                    'name': 'Unknown',
                    'email': '',
                    'phone': '',
                    'summary': '',
                    'experience': [],
                    'education': [],
                    'skills': []
                }

        except Exception as e:
            logger.error(f"Failed to parse profile PDF: {str(e)}")
            raise

    def research_company(self, company_name: str) -> Dict:
        """Research company using Perplexity API

        Args:
            company_name: Company name to research

        Returns:
            Dict with company information
        """
        if not self.perplexity_key:
            logger.warning("Perplexity API key not configured")
            return {
                'company': company_name,
                'info': 'Company research not available (API key not configured)'
            }

        try:
            # Use Tavily for web search as alternative to Perplexity
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=TAVILY_API_KEY)

            search_query = f"{company_name} company culture values mission products services"
            results = tavily.search(query=search_query, max_results=3)

            # Combine search results
            company_info = "\n\n".join([r.get('content', '') for r in results.get('results', [])])

            return {
                'company': company_name,
                'info': company_info,
                'sources': [r.get('url', '') for r in results.get('results', [])]
            }

        except Exception as e:
            logger.error(f"Company research failed: {str(e)}")
            return {
                'company': company_name,
                'info': f'Company research failed: {str(e)}'
            }

    def generate_ats_resume(
        self,
        profile_data: Dict,
        company_name: str,
        job_description: str,
        target_ats_score: int = 90,
        job_url: str = None,
        company_research: Dict = None
    ) -> Dict:
        """Generate ATS-optimized resume tailored to job description

        Args:
            profile_data: Parsed profile data from parse_profile_pdf()
            company_name: Target company name
            job_description: Full job description
            target_ats_score: Target ATS score (0-100)
            job_url: Optional job posting URL
            company_research: Optional company research data

        Returns:
            Dict with generated resume: {
                'resume_text': str,
                'ats_score': int,
                'matched_keywords': List[str],
                'suggestions': List[str]
            }
        """
        logger.info(f"Generating ATS resume for {company_name}, target score: {target_ats_score}")

        # Build context
        company_context = ""
        if company_research:
            company_context = f"\n\nCompany Research:\n{company_research.get('info', '')}"

        prompt = f"""Generate an ATS-optimized resume tailored to this specific job:

CANDIDATE PROFILE:
{json.dumps(profile_data, indent=2)}

TARGET COMPANY: {company_name}
{f'JOB URL: {job_url}' if job_url else ''}

JOB DESCRIPTION:
{job_description}

{company_context}

TARGET ATS SCORE: {target_ats_score}/100

INSTRUCTIONS:
1. Create a professionally formatted resume tailored to this specific job
2. Optimize for ATS (Applicant Tracking Systems) with target score {target_ats_score}/100
3. Extract and incorporate keywords from the job description
4. Highlight relevant experience and skills that match the job requirements
5. Use action verbs and quantifiable achievements
6. Ensure proper formatting with clear sections
7. Match the tone and language to the company culture (if researched)
8. Prioritize most relevant information first

Return as JSON with this structure:
{{
    "resume_text": "The complete formatted resume text with proper sections",
    "ats_score": 95,
    "matched_keywords": ["keyword1", "keyword2"],
    "key_strengths": ["strength1", "strength2"],
    "tailoring_notes": ["note1", "note2"]
}}

Generate a highly optimized, professional resume. Return ONLY valid JSON."""

        if self.model_mode == "api":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=6000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            result_text = response.content[0].text.strip()
        elif self.model_mode == "grok":
            result_text = self.grok_handler.generate_content(prompt, max_tokens=6000)
        else:  # local
            result_text = self.local_handler.generate_text(prompt, max_tokens=6000)

        # Extract JSON from response
        try:
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start != -1 and end > start:
                resume_data = json.loads(result_text[start:end])
                logger.info(f"Generated resume with ATS score: {resume_data.get('ats_score', 'N/A')}")
                return resume_data
            else:
                raise ValueError("Failed to extract JSON from response")
        except Exception as e:
            logger.error(f"Failed to parse resume generation response: {str(e)}")
            # Return fallback
            return {
                'resume_text': result_text,
                'ats_score': 70,
                'matched_keywords': [],
                'key_strengths': [],
                'tailoring_notes': ['Resume generated but structured analysis failed']
            }

    def analyze_job_match(
        self,
        profile_data: Dict,
        job_description: str
    ) -> Dict:
        """Analyze how well profile matches job requirements

        Args:
            profile_data: Parsed profile data
            job_description: Job description text

        Returns:
            Dict with match analysis: {
                'match_score': int (0-100),
                'matched_requirements': List[str],
                'missing_requirements': List[str],
                'recommendations': List[str]
            }
        """
        logger.info("Analyzing job match")

        prompt = f"""Analyze how well this candidate matches the job requirements:

CANDIDATE PROFILE:
{json.dumps(profile_data, indent=2)}

JOB DESCRIPTION:
{job_description}

Provide a detailed match analysis. Return as JSON:
{{
    "match_score": 85,
    "matched_requirements": ["requirement that candidate meets"],
    "missing_requirements": ["requirement candidate lacks"],
    "gap_areas": ["skill area to improve"],
    "recommendations": ["specific recommendation for candidate"],
    "competitive_advantages": ["unique strengths for this role"]
}}

Be specific and actionable. Return ONLY valid JSON."""

        if self.model_mode == "api":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            result_text = response.content[0].text.strip()
        elif self.model_mode == "grok":
            result_text = self.grok_handler.generate_content(prompt, max_tokens=2000)
        else:  # local
            result_text = self.local_handler.generate_text(prompt, max_tokens=2000)

        # Extract JSON
        try:
            start = result_text.find('{')
            end = result_text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(result_text[start:end])
        except:
            pass

        # Fallback
        return {
            'match_score': 70,
            'matched_requirements': [],
            'missing_requirements': [],
            'gap_areas': [],
            'recommendations': ['Unable to perform detailed analysis'],
            'competitive_advantages': []
        }

    def extract_job_keywords(self, job_description: str) -> List[str]:
        """Extract important keywords from job description

        Args:
            job_description: Job description text

        Returns:
            List of important keywords
        """
        prompt = f"""Extract the most important keywords from this job description that should appear in a resume:

{job_description}

Focus on:
- Technical skills and tools
- Required qualifications
- Key responsibilities
- Industry-specific terms
- Action verbs and competencies

Return as JSON array: ["keyword1", "keyword2", ...]
Return ONLY valid JSON array."""

        try:
            if self.model_mode == "api":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=1000,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.content[0].text.strip()
            elif self.model_mode == "grok":
                result_text = self.grok_handler.generate_content(prompt, max_tokens=1000)
            else:  # local
                result_text = self.local_handler.generate_text(prompt, max_tokens=1000)

            # Extract JSON array
            start = result_text.find('[')
            end = result_text.rfind(']') + 1
            if start != -1 and end > start:
                return json.loads(result_text[start:end])
        except:
            pass

        return []
