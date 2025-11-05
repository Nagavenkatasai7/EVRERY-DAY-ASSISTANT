"""
Cover Letter Generator using Claude API with cover letter knowledge
"""
import os
import json
from dotenv import load_dotenv
import anthropic
from pathlib import Path

load_dotenv()

class CoverLetterGenerator:
    def __init__(self, knowledge_path="coverletter_knowledge_base.md"):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.coverletter_knowledge = self._load_coverletter_knowledge(knowledge_path)

    def _load_coverletter_knowledge(self, knowledge_path):
        """Load cover letter knowledge base"""
        try:
            with open(knowledge_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Could not load cover letter knowledge: {e}")
            return ""

    def generate_cover_letter(self, profile_text, job_analysis, company_research=None, resume_content=None):
        """
        Generate professional cover letter using Claude

        Args:
            profile_text: Raw text from Profile.pdf
            job_analysis: Analyzed job description (from JobAnalyzer)
            company_research: Optional company research from Perplexity
            resume_content: Optional - the generated resume for alignment

        Returns:
            dict with 'content' (markdown/text cover letter) and 'success' status
        """

        # Build the prompt
        prompt = self._build_coverletter_prompt(profile_text, job_analysis, company_research, resume_content)

        try:
            print("Generating professional cover letter with Claude...")

            message = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=8000,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = message.content[0].text

            # Clean up the response
            cleaned_text = self._clean_cover_letter_output(response_text)

            return {
                "content": cleaned_text,
                "success": True
            }

        except Exception as e:
            print(f"Error generating cover letter: {e}")
            return {
                "content": "",
                "success": False,
                "error": str(e)
            }

    def _clean_cover_letter_output(self, text):
        """Remove any notes or commentary from the cover letter"""
        import re

        # Remove common patterns
        patterns_to_remove = [
            r'\n\s*#+\s*Notes.*$',
            r'\n\s*#+\s*Tips.*$',
            r'\n\s*---+\s*\n\s*\*\*.*Notes.*$',
        ]

        cleaned = text
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.MULTILINE | re.DOTALL)

        return cleaned.strip()

    def _build_coverletter_prompt(self, profile_text, job_analysis, company_research=None, resume_content=None):
        """Build comprehensive prompt for Claude"""

        company_name = job_analysis.get("company_name", "the company")
        job_title = job_analysis.get("job_title", "the position")
        keywords = job_analysis.get("keywords", [])
        required_skills = job_analysis.get("required_skills", [])
        responsibilities = job_analysis.get("key_responsibilities", [])

        # Build company research section
        company_section = ""
        if company_research:
            company_section = f"""
## Company Research
{company_research.get('research', '')}
"""

        # Build resume context if available
        resume_section = ""
        if resume_content:
            resume_section = f"""
## Generated Resume Context
The candidate has already created a resume for this position. Please ensure the cover letter complements (not repeats) the resume and highlights different aspects or adds storytelling context.

Resume Summary (first 500 chars):
{resume_content[:500]}...
"""

        prompt = f"""You are an expert cover letter writer with deep knowledge of modern cover letter best practices, storytelling, and professional communication.

# Your Task
Create a compelling, professional cover letter for {company_name} - {job_title} position that will capture the hiring manager's attention and complement the candidate's resume.

# Cover Letter Writing Knowledge Base
{self.coverletter_knowledge[:15000]}

# Candidate Profile
{profile_text}

# Target Job Analysis
Company: {company_name}
Job Title: {job_title}
Required Skills: {', '.join(required_skills[:10]) if required_skills else 'See job description'}
Key Responsibilities: {', '.join(responsibilities[:5]) if responsibilities else 'See job description'}
Key Keywords: {', '.join(keywords[:20]) if keywords else 'Extract from job description'}

Full Job Analysis:
{json.dumps(job_analysis, indent=2)}

{company_section}

{resume_section}

# Cover Letter Generation Instructions

## Critical Requirements:

1. **Format & Structure**:
   - Professional business letter format
   - Include: Date, Hiring Manager/Company Address, Greeting, 3-4 Body Paragraphs, Closing
   - Length: 250-400 words (3-4 paragraphs max)
   - Use proper business letter spacing

2. **Opening Paragraph (Hook)**:
   - Attention-grabbing first sentence
   - State the position clearly
   - Briefly mention your strongest qualification or achievement
   - Show enthusiasm for the role

3. **Body Paragraphs (Value Proposition)**:
   - Paragraph 2: Tell a compelling story that demonstrates relevant skills
   - Paragraph 3: Connect your experience to company needs
   - Use specific examples with quantifiable results
   - Show you understand the company and role
   - Demonstrate cultural fit

4. **Closing Paragraph (Call to Action)**:
   - Express enthusiasm
   - Reference availability for interview
   - Thank them for consideration
   - Professional sign-off

5. **Writing Style**:
   - Professional yet personable tone
   - Active voice, strong action verbs
   - Specific and concrete (avoid generic statements)
   - Show personality while maintaining professionalism
   - No clichés or overused phrases
   - Natural keyword integration

6. **Content Strategy**:
   - DO NOT simply repeat the resume
   - Add context, storytelling, and personality
   - Explain WHY you're interested in this company specifically
   - Demonstrate you've researched the company
   - Address how you can solve their specific challenges
   - Show passion for the role/industry

## Output Format (FOLLOW THIS EXACT STRUCTURE):

[Date]

[Your Name]
[Street Address
City, State, Zip]
[Phone Number]
[Email]
[LinkedIn profile and/or website address]

[Hiring Manager Name]
[Title]
[Company Name]
[Company Address
City, State, Zip]

Dear [Hiring Manager Name],

[First Paragraph - Introduction]
In one to three sentences, explain why you are writing and mention the specific position you are applying for. Highlight the main experience or qualification you have that would make you ideal for this job.

[Middle Paragraph(s) - Your Value Proposition]
This is where you sell yourself. Focus on recent achievements and use strong verbs to describe your skills. Explain how your skills and qualifications will make you a valuable asset to the company. Use specific examples with quantifiable results.

[Closing Paragraph]
Thank the reader for their time and attention. Reiterate your interest and enthusiasm about the position. Mention that you look forward to hearing from them shortly.

Thank you,
[Your Full Name]

---

**IMPORTANT OUTPUT REQUIREMENTS**:
- Generate ONLY the cover letter in the format above
- Do NOT include any notes, tips, or commentary
- Do NOT add explanatory text before or after
- Output should be pure cover letter content only
- Use the candidate's actual name and contact information from their profile
- Use today's date
- Be specific to {company_name} and the {job_title} role

Generate the professional cover letter now (cover letter only, no additional notes):"""

        return prompt

def main():
    """Test cover letter generator"""
    # Sample data
    profile_text = "Sample profile content..."
    job_analysis = {
        "company_name": "Google",
        "job_title": "Senior Software Engineer",
        "required_skills": ["Python", "Distributed Systems", "Cloud"],
        "keywords": ["Python", "Cloud", "Scalability"],
        "key_responsibilities": ["Design scalable systems", "Lead technical projects"]
    }

    generator = CoverLetterGenerator()
    result = generator.generate_cover_letter(profile_text, job_analysis)

    if result['success']:
        print("✓ Cover letter generated successfully")
        print(f"\nContent length: {len(result['content'])} characters")
        print("\nFirst 500 characters:")
        print(result['content'][:500])
    else:
        print(f"✗ Cover letter generation failed: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()
