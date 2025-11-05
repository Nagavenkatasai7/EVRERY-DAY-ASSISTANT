"""
Claude API Analyzer
Handles AI-powered analysis of research documents using Claude Sonnet 4.5
"""

import time
from typing import List, Dict, Optional
from pathlib import Path
import anthropic
from anthropic import APIError, APIConnectionError, RateLimitError as AnthropicRateLimitError

from config.settings import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    CLAUDE_MAX_TOKENS,
    CLAUDE_TEMPERATURE,
    CLAUDE_REQUEST_TIMEOUT,
    CLAUDE_MAX_RETRIES,
    CLAUDE_RETRY_DELAY,
    EXPERT_SYSTEM_PROMPT,
    ANALYSIS_PROMPT_TEMPLATE,
    SYNTHESIS_PROMPT_TEMPLATE
)
from utils.logger import get_logger
from utils.exceptions import ClaudeAPIError, RateLimitError, AuthenticationError
from utils.image_utils import image_to_base64

logger = get_logger(__name__)


class ClaudeAnalyzer:
    """
    Analyzes research documents using Claude Sonnet 4.5
    """

    def __init__(self):
        """Initialize Claude analyzer"""
        try:
            self.client = anthropic.Anthropic(
                api_key=ANTHROPIC_API_KEY,
                timeout=CLAUDE_REQUEST_TIMEOUT
            )
            self.model = CLAUDE_MODEL
            logger.info(f"Claude analyzer initialized with model: {self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize Claude client: {str(e)}")
            raise ClaudeAPIError(f"Initialization failed: {str(e)}")

    def _make_api_call(self, messages: List[Dict], system_prompt: str, max_tokens: int = CLAUDE_MAX_TOKENS) -> str:
        """
        Make API call to Claude with retry logic

        Args:
            messages: List of message dictionaries
            system_prompt: System prompt
            max_tokens: Maximum tokens in response

        Returns:
            Response text

        Raises:
            ClaudeAPIError: If API call fails
            RateLimitError: If rate limit exceeded
            AuthenticationError: If authentication fails
        """
        for attempt in range(CLAUDE_MAX_RETRIES):
            try:
                logger.debug(f"Making Claude API call (attempt {attempt + 1}/{CLAUDE_MAX_RETRIES})")

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=CLAUDE_TEMPERATURE,
                    system=[{
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}  # Enable prompt caching
                    }],
                    messages=messages
                )

                # Extract text from response
                if response.content and len(response.content) > 0:
                    result_text = response.content[0].text

                    # Log usage for monitoring
                    if hasattr(response, 'usage'):
                        logger.info(f"API usage - Input: {response.usage.input_tokens}, "
                                  f"Output: {response.usage.output_tokens}")

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

    def analyze_text_chunk(
        self,
        text: str,
        doc_name: str,
        page_num: int,
        section_name: Optional[str] = None,
        images: Optional[List] = None
    ) -> Dict:
        """
        Analyze a text chunk with optional images

        Args:
            text: Text content to analyze
            doc_name: Document name
            page_num: Page number
            section_name: Section name
            images: Optional list of PIL images

        Returns:
            Dictionary with analysis results
        """
        try:
            logger.info(f"Analyzing chunk from {doc_name}, page {page_num}")

            # Prepare prompt
            prompt = ANALYSIS_PROMPT_TEMPLATE.format(
                doc_name=doc_name,
                page_num=page_num,
                section_name=section_name or "Unknown Section",
                content=text
            )

            # Prepare messages with text
            content = [{"type": "text", "text": prompt}]

            # Add images if provided
            if images:
                for img in images[:3]:  # Limit to 3 images per chunk
                    try:
                        img_base64 = image_to_base64(img["image"])
                        content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": f"image/{img['format'].lower()}",
                                "data": img_base64
                            }
                        })
                        logger.debug(f"Added image {img['index']} to analysis")
                    except Exception as e:
                        logger.warning(f"Failed to add image to analysis: {str(e)}")

            messages = [{"role": "user", "content": content}]

            # Make API call
            analysis_text = self._make_api_call(messages, EXPERT_SYSTEM_PROMPT)

            return {
                "analysis": analysis_text,
                "doc_name": doc_name,
                "page": page_num,
                "section": section_name,
                "has_images": images is not None and len(images) > 0,
                "image_count": len(images) if images else 0
            }

        except Exception as e:
            logger.error(f"Failed to analyze chunk: {str(e)}")
            raise ClaudeAPIError(f"Analysis failed: {str(e)}")

    def synthesize_insights(
        self,
        retrieved_chunks: List[Dict],
        topic: Optional[str] = None
    ) -> Dict:
        """
        Synthesize insights from multiple retrieved chunks

        Args:
            retrieved_chunks: List of chunk dictionaries from RAG search
            topic: Optional topic description

        Returns:
            Dictionary with synthesis results
        """
        try:
            logger.info(f"Synthesizing insights from {len(retrieved_chunks)} chunks")

            if not retrieved_chunks:
                return {
                    "synthesis": "No relevant content found for synthesis.",
                    "chunk_count": 0
                }

            # Prepare retrieved content
            content_parts = []
            for i, chunk in enumerate(retrieved_chunks):
                text = chunk.get("text", "")
                metadata = chunk.get("metadata", {})
                source = metadata.get("source", "Unknown")
                section = metadata.get("section", "Unknown Section")

                content_parts.append(
                    f"**Source {i+1}**: {source}, §{section}\n{text}\n"
                )

            retrieved_content = "\n---\n".join(content_parts)

            # Prepare prompt
            prompt = SYNTHESIS_PROMPT_TEMPLATE.format(
                doc_count=len(set(c.get("metadata", {}).get("doc_name", "") for c in retrieved_chunks)),
                topic=topic or "research findings",
                retrieved_content=retrieved_content
            )

            messages = [{"role": "user", "content": prompt}]

            # Make API call
            synthesis_text = self._make_api_call(messages, EXPERT_SYSTEM_PROMPT, max_tokens=6000)

            return {
                "synthesis": synthesis_text,
                "chunk_count": len(retrieved_chunks),
                "doc_count": len(set(c.get("metadata", {}).get("doc_name", "") for c in retrieved_chunks))
            }

        except Exception as e:
            logger.error(f"Failed to synthesize insights: {str(e)}")
            raise ClaudeAPIError(f"Synthesis failed: {str(e)}")

    def generate_executive_summary(self, documents_data: List[Dict]) -> str:
        """
        Generate executive summary of all documents

        Args:
            documents_data: List of document data dictionaries

        Returns:
            Executive summary text
        """
        try:
            logger.info(f"Generating executive summary for {len(documents_data)} documents")

            # Extract key information from documents
            doc_summaries = []
            for doc in documents_data:
                doc_name = doc.get("doc_name", "Unknown")
                metadata = doc.get("metadata", {})
                title = metadata.get("title", doc_name)
                author = metadata.get("author", "Unknown")
                page_count = len(doc.get("pages", []))

                # Get first few pages text for context
                first_pages_text = ""
                for page in doc.get("pages", [])[:3]:
                    first_pages_text += page.get("text", "")[:500] + "\n"

                doc_summaries.append(
                    f"**{title}** by {author} ({page_count} pages)\n{first_pages_text}\n"
                )

            combined_context = "\n---\n".join(doc_summaries)

            prompt = f"""Based on the following research documents, provide a comprehensive executive summary.

Documents:
{combined_context}

Provide an executive summary that includes:
1. Overview of the research area and topics covered
2. Key findings and contributions across all documents
3. Common themes and patterns
4. Methodological approaches used
5. Significance and potential impact

Keep the summary concise but comprehensive (500-800 words).
"""

            messages = [{"role": "user", "content": prompt}]

            summary = self._make_api_call(messages, EXPERT_SYSTEM_PROMPT, max_tokens=4000)

            logger.info("Executive summary generated successfully")
            return summary

        except Exception as e:
            logger.error(f"Failed to generate executive summary: {str(e)}")
            return f"Error generating summary: {str(e)}"

    def analyze_with_rag(
        self,
        rag_system,
        analysis_queries: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Perform comprehensive analysis using RAG system

        Args:
            rag_system: RAGSystem instance
            analysis_queries: Optional list of specific queries to analyze

        Returns:
            List of analysis results
        """
        try:
            logger.info("Starting comprehensive RAG-based analysis")

            # Default queries if none provided
            if not analysis_queries:
                analysis_queries = [
                    "What are the main research questions and objectives?",
                    "What methodologies are used in these studies?",
                    "What are the key findings and contributions?",
                    "What are the limitations and future directions?",
                    "How do these studies relate to each other?"
                ]

            results = []

            for query in analysis_queries:
                logger.info(f"Analyzing query: {query}")

                # Get relevant context from RAG
                context, metadata_list = rag_system.get_relevant_context(query, max_chunks=5)

                if not context:
                    logger.warning(f"No relevant context found for query: {query}")
                    continue

                # Synthesize insights
                synthesis = self.synthesize_insights(
                    [{"text": context, "metadata": m} for m in metadata_list],
                    topic=query
                )

                results.append({
                    "query": query,
                    "synthesis": synthesis["synthesis"],
                    "sources": metadata_list
                })

            logger.info(f"Completed analysis of {len(results)} queries")
            return results

        except Exception as e:
            logger.error(f"RAG analysis failed: {str(e)}")
            raise ClaudeAPIError(f"RAG analysis failed: {str(e)}")
