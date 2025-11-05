"""
Comprehensive Research Analyzer
Creates detailed research notes with cross-document synthesis
"""

import time
from typing import List, Dict, Optional
import anthropic
from anthropic import APIError, APIConnectionError, RateLimitError as AnthropicRateLimitError

from config.settings import (
    MODEL_MODE,
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    CLAUDE_MAX_TOKENS,
    CLAUDE_TEMPERATURE,
    CLAUDE_REQUEST_TIMEOUT,
    CLAUDE_MAX_RETRIES,
    CLAUDE_RETRY_DELAY,
    EXPERT_SYSTEM_PROMPT,
    SYNTHESIS_PROMPT_TEMPLATE,
    ENABLE_PROMPT_CACHING
)
from utils.logger import get_logger
from utils.exceptions import ClaudeAPIError, RateLimitError, AuthenticationError

logger = get_logger(__name__)


class ComprehensiveAnalyzer:
    """
    Creates comprehensive research notes with:
    - Deep cross-document synthesis
    - Detailed theoretical analysis
    - Specific citations and sources
    - Connected insights across papers
    """

    def __init__(self, model_mode: str = None, local_model_name: str = None):
        """Initialize comprehensive analyzer

        Args:
            model_mode: "api" for Claude API, "grok" for xAI Grok, or "local" for local LLM (defaults to settings)
            local_model_name: Name of local model to use (only for local mode)
        """
        try:
            self.model_mode = model_mode or MODEL_MODE
            logger.info(f"Initializing comprehensive analyzer in {self.model_mode} mode")

            if self.model_mode == "api":
                # Initialize Claude API client
                self.client = anthropic.Anthropic(
                    api_key=ANTHROPIC_API_KEY,
                    timeout=CLAUDE_REQUEST_TIMEOUT
                )
                self.model = CLAUDE_MODEL
                self.local_handler = None
                self.grok_handler = None
                logger.info(f"Comprehensive analyzer initialized with Claude API: {self.model}")

            elif self.model_mode == "grok":
                # Initialize Grok API handler
                from src.grok_handler import GrokHandler
                from config.settings import GROK_MODEL

                self.grok_handler = GrokHandler()
                self.client = None
                self.local_handler = None
                self.model = GROK_MODEL
                logger.info(f"Comprehensive analyzer initialized with Grok API: {self.model}")

            elif self.model_mode == "local":
                # Initialize local LLM handler with selected model
                from src.local_llm_handler import LocalLLMHandler
                from config.settings import LOCAL_MODEL_NAME

                # Use provided model name or default from settings
                model_to_use = local_model_name or LOCAL_MODEL_NAME

                self.local_handler = LocalLLMHandler(model_name=model_to_use)
                self.client = None
                self.grok_handler = None
                self.model = self.local_handler.model_name
                logger.info(f"Comprehensive analyzer initialized with local model: {self.model}")

            else:
                raise ValueError(f"Invalid model_mode: {self.model_mode}. Must be 'api', 'grok', or 'local'")

        except Exception as e:
            logger.error(f"Failed to initialize analyzer: {str(e)}")
            raise ClaudeAPIError(f"Initialization failed: {str(e)}")

    def _make_api_call(self, messages: List[Dict], system_prompt: str, max_tokens: int = CLAUDE_MAX_TOKENS, use_cache: bool = True) -> str:
        """Make API call (either Claude API or local LLM) with optional prompt caching

        Args:
            messages: List of message dictionaries
            system_prompt: System prompt text
            max_tokens: Maximum tokens for response
            use_cache: Whether to use prompt caching (default: True for cost savings)

        Returns:
            Response text from API
        """

        # Route to local LLM if in local mode
        if self.model_mode == "local":
            return self.local_handler.make_api_call(messages, system_prompt, max_tokens)

        # Route to Grok API if in grok mode
        if self.model_mode == "grok":
            from config.settings import GROK_MAX_TOKENS, GROK_TEMPERATURE
            # Convert messages format and make Grok API call
            grok_messages = [{"role": "system", "content": system_prompt}] + messages
            return self.grok_handler.generate_response(
                messages=grok_messages,
                max_tokens=min(max_tokens, GROK_MAX_TOKENS),
                temperature=GROK_TEMPERATURE
            )

        # Otherwise use Claude API with prompt caching
        for attempt in range(CLAUDE_MAX_RETRIES):
            try:
                logger.debug(f"Making Claude API call (attempt {attempt + 1}/{CLAUDE_MAX_RETRIES}, caching: {use_cache})")

                # Build system message with prompt caching if enabled
                if use_cache:
                    system_message = [{
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}
                    }]
                else:
                    system_message = system_prompt

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=CLAUDE_TEMPERATURE,
                    system=system_message,
                    messages=messages
                )

                if response.content and len(response.content) > 0:
                    result_text = response.content[0].text

                    # Log token usage with cache information
                    if hasattr(response, 'usage'):
                        usage = response.usage
                        cache_read = getattr(usage, 'cache_read_input_tokens', 0)
                        cache_creation = getattr(usage, 'cache_creation_input_tokens', 0)

                        logger.info(
                            f"API usage - Input: {usage.input_tokens}, Output: {usage.output_tokens}, "
                            f"Cache read: {cache_read}, Cache creation: {cache_creation}"
                        )

                        # Log cost savings from caching
                        if cache_read > 0:
                            savings_pct = (cache_read / (usage.input_tokens + cache_read)) * 100
                            logger.info(f"💰 Cache savings: {cache_read} tokens ({savings_pct:.1f}% of input)")

                    return result_text

                raise ClaudeAPIError("Empty response from Claude API")

            except AnthropicRateLimitError as e:
                logger.warning(f"Rate limit exceeded (attempt {attempt + 1})")
                if attempt < CLAUDE_MAX_RETRIES - 1:
                    wait_time = CLAUDE_RETRY_DELAY * (attempt + 1)
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    raise RateLimitError(f"Rate limit exceeded after {CLAUDE_MAX_RETRIES} attempts")

            except APIConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt + 1}): {str(e)}")
                if attempt < CLAUDE_MAX_RETRIES - 1:
                    time.sleep(CLAUDE_RETRY_DELAY)
                else:
                    raise ClaudeAPIError(f"Connection failed after {CLAUDE_MAX_RETRIES} attempts: {str(e)}")

            except anthropic.AuthenticationError as e:
                logger.error(f"Authentication error: {str(e)}")
                raise AuthenticationError(f"Invalid API key: {str(e)}")

            except APIError as e:
                logger.error(f"Claude API error: {str(e)}")
                if attempt < CLAUDE_MAX_RETRIES - 1:
                    time.sleep(CLAUDE_RETRY_DELAY)
                else:
                    raise ClaudeAPIError(f"API error after {CLAUDE_MAX_RETRIES} attempts: {str(e)}")

            except Exception as e:
                logger.error(f"Unexpected error in API call: {str(e)}")
                raise ClaudeAPIError(f"Unexpected error: {str(e)}")

        raise ClaudeAPIError("Max retries exceeded")

    def _make_api_call_with_retry(self, messages: List[Dict], system_prompt: str, max_tokens: int = CLAUDE_MAX_TOKENS) -> str:
        """
        Make API call with retry logic and prompt caching (wrapper for chatbot compatibility)

        This method is used by the chatbot and other components that need
        the retry logic with automatic prompt caching for cost optimization.

        Args:
            messages: List of message dictionaries
            system_prompt: System prompt text
            max_tokens: Maximum tokens for response

        Returns:
            Response text from API
        """
        # Use caching based on global setting (enabled by default for cost savings)
        return self._make_api_call(messages, system_prompt, max_tokens, use_cache=ENABLE_PROMPT_CACHING)

    def create_comprehensive_summary(
        self,
        rag_system,
        documents_data: List[Dict],
        focus_areas: Optional[List[str]] = None,
        report_mode: str = "quick"
    ) -> Dict:
        """
        Create comprehensive notes from all documents with deep theoretical analysis

        Args:
            rag_system: RAGSystem instance
            documents_data: List of processed document data
            focus_areas: Optional list of specific areas to focus on
            report_mode: "quick" or "full" report type (images removed)

        Returns:
            Dictionary with comprehensive notes and metadata
        """
        try:
            logger.info(f"Creating comprehensive research notes with deep synthesis")

            # Default focus areas if none provided
            if not focus_areas:
                focus_areas = [
                    "What are the main research topics and themes across all papers?",
                    "What are the key methodologies and approaches used?",
                    "What are the most significant findings and contributions?",
                    "How do these papers relate to and build upon each other?",
                    "What are the practical implications and applications?",
                    "What limitations and future directions are identified?"
                ]

            # Generate executive summary
            executive_summary = self._generate_executive_summary(documents_data)

            # Analyze each focus area with cross-document synthesis
            detailed_sections = []

            for i, focus_area in enumerate(focus_areas, 1):
                logger.info(f"Analyzing focus area {i}/{len(focus_areas)}: {focus_area}")

                # Get relevant context from ALL documents
                context, metadata_list = rag_system.get_relevant_context(focus_area, max_chunks=10)

                if not context:
                    logger.warning(f"No relevant context found for: {focus_area}")
                    continue

                # Synthesize comprehensive text-only analysis
                synthesis = self._synthesize_text_only(
                    focus_area,
                    context,
                    metadata_list,
                    len(documents_data)
                )

                detailed_sections.append({
                    'title': focus_area,
                    'content': synthesis,
                    'sources': metadata_list,
                    'images': []  # No images in notes format
                })

            # Calculate statistics
            total_pages = sum(len(d.get('pages', [])) for d in documents_data)

            result = {
                'executive_summary': executive_summary,
                'detailed_sections': detailed_sections,
                'doc_count': len(documents_data),
                'total_pages': total_pages,
                'total_images': 0,  # No images extracted for notes
                'focus_areas_analyzed': len(detailed_sections)
            }

            logger.info(f"Comprehensive notes complete: {len(detailed_sections)} sections generated")
            return result

        except Exception as e:
            logger.error(f"Failed to create comprehensive notes: {str(e)}")
            raise ClaudeAPIError(f"Comprehensive notes failed: {str(e)}")

    def _generate_executive_summary(self, documents_data: List[Dict]) -> str:
        """Generate an executive summary reading ALL pages from all documents"""
        try:
            logger.info("Generating comprehensive executive summary from ALL pages")

            # Extract FULL content from ALL documents
            doc_overviews = []
            for doc in documents_data:
                doc_name = doc.get("doc_name", "Unknown")
                pages = doc.get("pages", [])
                page_count = len(pages)

                # Get ALL pages text (not just first few)
                full_text = ""
                for page in pages:
                    page_text = page.get("text", "")
                    if page_text:
                        full_text += page_text + "\n\n"

                # Limit to reasonable size for API (take key sections throughout document)
                if len(full_text) > 50000:
                    # Take beginning, middle, and end to ensure full coverage
                    start = full_text[:15000]
                    middle_start = len(full_text) // 2 - 7500
                    middle = full_text[middle_start:middle_start + 15000]
                    end = full_text[-15000:]
                    full_text = start + "\n\n[... middle sections ...]\n\n" + middle + "\n\n[... later sections ...]\n\n" + end

                doc_overviews.append(
                    f"**{doc_name}** ({page_count} pages - FULL DOCUMENT TEXT)\n{full_text}\n"
                )

            combined_overview = "\n\n" + "="*80 + "\n\n".join(doc_overviews)

            prompt = f"""Based on these {len(documents_data)} research documents, create a comprehensive executive summary.

Documents Overview:
{combined_overview}

Write a detailed executive summary (4-6 paragraphs) that:

1. **Overview**: Describe the overall research area and what these papers collectively address
2. **Key Themes**: Identify the main themes and topics across all documents
3. **Major Findings**: Highlight the most significant findings and contributions
4. **Methodological Approaches**: Summarize the research methods and approaches used
5. **Connections**: Explain how these papers relate to each other
6. **Significance**: Explain why this research matters and its potential impact

Make it informative, well-structured, and engaging. Connect the dots between papers.
"""

            messages = [{"role": "user", "content": prompt}]
            # Increased max_tokens for very detailed executive summary
            summary = self._make_api_call(messages, EXPERT_SYSTEM_PROMPT, max_tokens=8000)

            return summary

        except Exception as e:
            logger.error(f"Failed to generate executive summary: {str(e)}")
            return f"Error generating executive summary: {str(e)}"

    def _synthesize_text_only(
        self,
        topic: str,
        context: str,
        metadata_list: List[Dict],
        doc_count: int
    ) -> str:
        """Synthesize comprehensive text-only analysis with detailed theoretical content"""
        try:
            # Prepare text prompt for detailed notes
            text_prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
                topic=topic,
                doc_count=doc_count,
                retrieved_content=context
            )

            messages = [{"role": "user", "content": text_prompt}]

            # Increase max_tokens for very detailed theoretical analysis
            synthesis = self._make_api_call(messages, EXPERT_SYSTEM_PROMPT, max_tokens=8000)

            return synthesis

        except Exception as e:
            logger.error(f"Failed to synthesize text: {str(e)}")
            return f"Error during synthesis: {str(e)}"
