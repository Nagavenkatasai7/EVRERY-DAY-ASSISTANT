"""
Research Router for Resume Maker
Routes company research requests to Perplexity or Tavily based on configuration
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from .perplexity_client import PerplexityClient
    from src.web_search import WebSearchManager as WebSearchClient
except ImportError:
    from perplexity_client import PerplexityClient
    from src.web_search import WebSearchManager as WebSearchClient

load_dotenv()


class ResearchRouter:
    """Routes research requests to appropriate API"""

    def __init__(self, research_api=None):
        """
        Initialize research router

        Args:
            research_api: 'perplexity', 'tavily', or None (auto-detect from env)
        """
        # Determine which API to use
        if research_api is None:
            research_api = os.getenv('RESUME_RESEARCH_API', 'tavily').lower()

        self.research_api = research_api
        self.perplexity_client = None
        self.tavily_client = None

        # Initialize the appropriate client
        if self.research_api == 'perplexity':
            perplexity_key = os.getenv('PERPLEXITY_API_KEY')
            if perplexity_key and perplexity_key != 'your_perplexity_key_here':
                self.perplexity_client = PerplexityClient()
                print(f"✓ Research Router: Using Perplexity API")
            else:
                print("⚠️  Perplexity API key not configured, falling back to Tavily")
                self.research_api = 'tavily'

        if self.research_api == 'tavily':
            tavily_key = os.getenv('TAVILY_API_KEY')
            if tavily_key:
                self.tavily_client = WebSearchClient()
                print(f"✓ Research Router: Using Tavily API")
            else:
                print("⚠️  Tavily API key not configured, research disabled")
                self.research_api = None

    def research_company(self, company_name, job_title=None):
        """
        Research company using configured API

        Args:
            company_name: Name of the company
            job_title: Optional job title for more targeted research

        Returns:
            dict: Research results or None if research is disabled
        """
        if self.research_api is None:
            return None

        if self.research_api == 'perplexity' and self.perplexity_client:
            return self._research_with_perplexity(company_name, job_title)

        elif self.research_api == 'tavily' and self.tavily_client:
            return self._research_with_tavily(company_name, job_title)

        return None

    def _research_with_perplexity(self, company_name, job_title=None):
        """Research using Perplexity API"""
        try:
            result = self.perplexity_client.research_company(company_name, job_title)
            if result:
                return {
                    'company_name': company_name,
                    'research': result.get('research', ''),
                    'source': 'Perplexity AI'
                }
        except Exception as e:
            print(f"⚠️  Perplexity research failed: {e}")
        return None

    def _research_with_tavily(self, company_name, job_title=None):
        """Research using Tavily API"""
        try:
            # Build search query
            if job_title:
                query = f"{company_name} {job_title} technologies stack culture values"
            else:
                query = f"{company_name} company technologies culture values recent news"

            # Search with Tavily
            results = self.tavily_client.search(query, max_results=3)

            if results:
                # Combine search results into research summary
                research_text = f"Company Research for {company_name}:\n\n"

                for i, result in enumerate(results[:3], 1):
                    research_text += f"{i}. {result.get('title', 'N/A')}\n"
                    research_text += f"   {result.get('content', 'No content available')}\n"
                    research_text += f"   Source: {result.get('url', 'N/A')}\n\n"

                return {
                    'company_name': company_name,
                    'research': research_text,
                    'source': 'Tavily Search'
                }
        except Exception as e:
            print(f"⚠️  Tavily research failed: {e}")
        return None

    def get_api_name(self):
        """Get the name of the currently active research API"""
        if self.research_api == 'perplexity':
            return 'Perplexity AI'
        elif self.research_api == 'tavily':
            return 'Tavily Search'
        else:
            return 'None (Disabled)'


def main():
    """Test research router"""
    print("Testing Research Router...\n")

    # Test with auto-detection
    router = ResearchRouter()
    print(f"Active API: {router.get_api_name()}\n")

    # Test company research
    result = router.research_company("Google", "Software Engineer")

    if result:
        print(f"✓ Research successful")
        print(f"Company: {result['company_name']}")
        print(f"Source: {result['source']}")
        print(f"Research: {result['research'][:200]}...")
    else:
        print("✗ Research failed or disabled")


if __name__ == "__main__":
    main()
