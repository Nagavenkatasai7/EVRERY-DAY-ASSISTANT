"""
Web Search Integration with Tavily AI
Provides web search capabilities for multi-source research with citation verification
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re
from urllib.parse import urlparse
from tavily import TavilyClient

from config.settings import TAVILY_API_KEY, ENABLE_WEB_SEARCH
from utils.logger import get_logger

logger = get_logger(__name__)

# Search configuration
MAX_WEB_RESULTS = 10  # Maximum web results per search
MAX_SEARCH_DEPTH = "advanced"  # Tavily search depth: basic or advanced
MIN_CONTENT_LENGTH = 5  # Minimum content length to be useful
MAX_RETRIES = 2  # Retry failed searches


class WebSearchManager:
    """
    Manages web search using Tavily AI for multi-source research

    Features:
    - Academic and general web search
    - Citation verification
    - Source diversity tracking
    - Content extraction and cleaning
    - Error handling and retries
    """

    def __init__(self):
        """Initialize Tavily client with error handling"""
        self.client = None
        self.tavily_client = None  # Alias for tests compatibility
        self.enabled = ENABLE_WEB_SEARCH
        self.search_count = 0
        self.max_results = MAX_WEB_RESULTS  # For test compatibility
        self.source_diversity = {
            "pdf": 0,
            "web": 0,
            "domains": set()
        }

        if not self.enabled:
            logger.info("ℹ️  Web search disabled in configuration")
            return

        try:
            if not TAVILY_API_KEY:
                logger.warning("⚠️  TAVILY_API_KEY not set - web search disabled")
                self.enabled = False
                return

            self.client = TavilyClient(api_key=TAVILY_API_KEY)
            self.tavily_client = self.client  # Alias for tests
            logger.info("✓ Tavily Web Search initialized successfully")
            logger.info(f"   🔍 Max results per search: {MAX_WEB_RESULTS}")
            logger.info(f"   📚 Search depth: {MAX_SEARCH_DEPTH}")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Tavily client: {str(e)}")
            self.enabled = False

    def search(
        self,
        query: str,
        max_results: int = MAX_WEB_RESULTS,
        search_depth: str = MAX_SEARCH_DEPTH,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Perform web search using Tavily AI

        Args:
            query: Search query
            max_results: Maximum number of results (default: 10)
            search_depth: "basic" or "advanced" (default: advanced)
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude

        Returns:
            List of search result dictionaries with content, url, title, etc.
        """
        # Check if client is available (either self.client or tavily_client for testing)
        client = self.client or self.tavily_client
        if not client:
            logger.warning("Web search not available")
            return []

        try:
            logger.info(f"🔍 Web search: '{query[:100]}...'")

            # Validate query
            if not query or len(query.strip()) < 3:
                logger.warning("Query too short for web search")
                return []

            # Prepare search parameters
            search_params = {
                "query": query,
                "max_results": min(max_results, MAX_WEB_RESULTS),
                "search_depth": search_depth,
                "include_answer": True,  # Get AI-generated answer
                "include_raw_content": True,  # Get full content
                "include_images": False  # We don't need images for text research
            }

            # Add domain filters if provided
            if include_domains:
                search_params["include_domains"] = include_domains
            if exclude_domains:
                search_params["exclude_domains"] = exclude_domains

            # Execute search with retry logic
            response = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    response = client.search(**search_params)
                    break
                except Exception as e:
                    if attempt < MAX_RETRIES:
                        logger.warning(f"Search attempt {attempt + 1} failed, retrying...")
                    else:
                        raise e

            if not response:
                logger.error("No response from Tavily API")
                return []

            # Process results
            results = self._process_search_results(response, query)

            # Limit results to max_results
            results = results[:max_results]

            # Update search count and diversity tracking
            self.search_count += 1
            for result in results:
                domain = self._extract_domain(result.get("url", ""))
                if domain:
                    self.source_diversity["domains"].add(domain)
                    self.source_diversity["web"] += 1

            logger.info(f"✓ Found {len(results)} web results")
            return results

        except Exception as e:
            logger.error(f"❌ Web search failed: {str(e)}")
            return []

    def _process_search_results(self, response: Dict, query: str) -> List[Dict]:
        """
        Process and clean search results from Tavily

        Args:
            response: Tavily API response
            query: Original search query

        Returns:
            List of processed result dictionaries
        """
        processed_results = []

        # Get results from response
        raw_results = response.get("results", [])

        for idx, result in enumerate(raw_results):
            try:
                # Extract core information
                url = result.get("url", "")
                title = result.get("title", "Untitled")
                content = result.get("content", "")
                raw_content = result.get("raw_content", "")
                score = result.get("score", 0.0)

                # Use raw content if available and longer
                if len(raw_content) > len(content):
                    content = raw_content

                # Clean and validate content
                content = self._clean_content(content)

                # Skip if content too short
                if len(content) < MIN_CONTENT_LENGTH:
                    logger.debug(f"Skipping result {idx + 1}: content too short")
                    continue

                # Extract domain (use URL if extraction fails)
                domain = self._extract_domain(url)
                if not domain:
                    # For malformed URLs, use the URL itself as domain
                    domain = url if url else "unknown"

                # Create processed result
                processed_result = {
                    "content": content,
                    "url": url,
                    "title": title,
                    "domain": domain,
                    "score": float(score),
                    "source_type": "web",
                    "timestamp": datetime.now().isoformat(),
                    "query": query,
                    "index": idx + 1
                }

                processed_results.append(processed_result)

            except Exception as e:
                logger.warning(f"Error processing result {idx + 1}: {str(e)}")
                continue

        return processed_results

    def _clean_content(self, content: str) -> str:
        """
        Clean and normalize content text

        Args:
            content: Raw content text

        Returns:
            Cleaned content
        """
        if not content:
            return ""

        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)

        # Remove HTML entities
        content = content.replace('&nbsp;', ' ')
        content = content.replace('&amp;', '&')
        content = content.replace('&lt;', '<')
        content = content.replace('&gt;', '>')

        # Remove URLs from content (often clutters the text)
        content = re.sub(r'http[s]?://\S+', '', content)

        # Trim and return
        return content.strip()

    def _extract_domain(self, url: str) -> Optional[str]:
        """
        Extract domain from URL

        Args:
            url: Full URL

        Returns:
            Domain name or None
        """
        try:
            if not url:
                return None

            parsed = urlparse(url)
            domain = parsed.netloc

            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]

            # Extract root domain (last 2 segments) if it has subdomains
            # e.g., subdomain.test.org -> test.org
            parts = domain.split('.')
            if len(parts) > 2:
                # Keep only the last 2 parts (domain.tld)
                domain = '.'.join(parts[-2:])

            return domain if domain else None

        except Exception:
            return None

    def verify_citation(self, citation: str, sources: List[Dict]) -> Dict:
        """
        Verify if a citation appears in source materials

        Args:
            citation: Text to verify
            sources: List of source dictionaries to check against

        Returns:
            Dictionary with verification results
        """
        try:
            if not citation or not sources:
                return {
                    "verified": False,
                    "confidence": 0.0,
                    "matching_sources": [],
                    "reason": "No citation or sources provided"
                }

            # Clean citation for comparison
            citation_clean = citation.lower().strip()

            # Check each source
            matching_sources = []
            for source in sources:
                content = source.get("content", "").lower()

                # Check if citation appears in content
                if citation_clean in content:
                    matching_sources.append({
                        "source_type": source.get("source_type", "unknown"),
                        "url": source.get("url", source.get("source", "unknown")),
                        "title": source.get("title", source.get("doc_name", "Untitled"))
                    })

            # Calculate confidence based on number of matches
            confidence = min(len(matching_sources) / 2.0, 1.0)  # Max at 2 sources

            return {
                "verified": len(matching_sources) > 0,
                "confidence": confidence,
                "matching_sources": matching_sources,
                "reason": f"Found in {len(matching_sources)} source(s)" if matching_sources
                         else "Not found in any source"
            }

        except Exception as e:
            logger.error(f"Citation verification failed: {str(e)}")
            return {
                "verified": False,
                "confidence": 0.0,
                "matching_sources": [],
                "reason": f"Verification error: {str(e)}"
            }

    def get_source_diversity_report(self) -> Dict:
        """
        Get report on source diversity

        Returns:
            Dictionary with diversity metrics
        """
        total_sources = self.source_diversity["pdf"] + self.source_diversity["web"]

        return {
            "total_sources": total_sources,
            "pdf_sources": self.source_diversity["pdf"],
            "web_sources": self.source_diversity["web"],
            "unique_domains": len(self.source_diversity["domains"]),
            "domains_list": sorted(list(self.source_diversity["domains"])),
            "diversity_score": len(self.source_diversity["domains"]) / max(self.source_diversity["web"], 1),
            "web_percentage": (self.source_diversity["web"] / total_sources * 100) if total_sources > 0 else 0
        }

    def update_pdf_count(self, count: int):
        """
        Update count of PDF sources for diversity tracking

        Args:
            count: Number of PDF sources
        """
        self.source_diversity["pdf"] = count

    def reset_diversity_tracking(self):
        """Reset source diversity tracking"""
        self.source_diversity = {
            "pdf": 0,
            "web": 0,
            "domains": set()
        }
        self.search_count = 0

    def get_source_diversity(self, web_results: List[Dict], pdf_results: List[Dict]) -> Dict:
        """
        Calculate source diversity metrics from web and PDF results

        Args:
            web_results: List of web search result dictionaries
            pdf_results: List of PDF result dictionaries

        Returns:
            Dictionary with diversity metrics
        """
        # Extract unique domains from web results
        domains = set()
        for result in web_results:
            domain = result.get('domain')
            if domain:
                domains.add(domain)

        return {
            'total_sources': len(web_results) + len(pdf_results),
            'web_sources': len(web_results),
            'pdf_sources': len(pdf_results),
            'unique_domains': len(domains),
            'domains_list': list(domains)
        }
