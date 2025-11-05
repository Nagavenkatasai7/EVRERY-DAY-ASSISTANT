"""
Perplexity API client for optional job/company research
"""
import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

class PerplexityClient:
    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai"

    def research_company(self, company_name, job_title=None):
        """
        Research company using Perplexity API
        Returns insights about the company that can be used in resume customization
        """
        if not self.api_key:
            print("Perplexity API key not found - skipping company research")
            return None

        # Build research query
        query = f"What are the key technologies, values, and culture at {company_name}?"
        if job_title:
            query = f"What technologies and skills are important for a {job_title} role at {company_name}? What is the company culture and values?"

        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that researches companies for job applications. Provide concise, factual information."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.2
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                research_data = result['choices'][0]['message']['content']
                return {
                    "company_name": company_name,
                    "research": research_data,
                    "query": query
                }
            else:
                print(f"Perplexity API error: {response.status_code}")
                return None

        except Exception as e:
            print(f"Error researching company: {e}")
            return None

    def research_job_url(self, job_url):
        """
        Research a specific job posting URL
        This is optional and may require web scraping capabilities
        """
        # For now, return None - could be enhanced with web scraping
        return None

def main():
    """Test Perplexity integration"""
    client = PerplexityClient()

    if client.api_key:
        print("Testing Perplexity API...")
        result = client.research_company("Google", "Software Engineer")

        if result:
            print("✓ Company research complete")
            print(json.dumps(result, indent=2))
        else:
            print("✗ Company research failed")
    else:
        print("ℹ Perplexity API key not configured - this feature is optional")

if __name__ == "__main__":
    main()
