"""
Interactive Chatbot for Document Q&A
Answers questions using RAG system across summary and source PDFs
"""

from typing import List, Dict, Optional, Tuple
from pathlib import Path

from src.document_session import DocumentSession
from src.rag_system import RAGSystem
from src.comprehensive_analyzer import ComprehensiveAnalyzer
from config.settings import EXPERT_SYSTEM_PROMPT
from utils.logger import get_logger
from utils.exceptions import ClaudeAPIError

logger = get_logger(__name__)


class DocumentChatbot:
    """Interactive chatbot for document Q&A"""

    def __init__(
        self,
        session: DocumentSession,
        model_mode: str = "api",
        local_model_name: Optional[str] = None
    ):
        """
        Initialize chatbot

        Args:
            session: DocumentSession to chat about
            model_mode: "api" or "local"
            local_model_name: Local model name if using local mode
        """
        self.session = session
        self.model_mode = model_mode
        self.local_model_name = local_model_name

        # Initialize RAG system
        self.rag_system = RAGSystem()

        # Load session's RAG store
        try:
            self.session.load_rag_system(self.rag_system)
            logger.info(f"Loaded RAG store for session: {session.session_id}")

            # Log session details for debugging
            logger.info(f"Session metadata: source_pdf_count={session.metadata.get('source_pdf_count')}, has_summary={session.metadata.get('has_summary')}")
            logger.info(f"Summary PDF name: {session.metadata.get('summary_pdf_name', 'NOT SET')}")
            logger.info(f"Source PDFs: {session.metadata.get('source_pdf_names', [])}")
            logger.info(f"RAG chunks loaded: {len(self.rag_system.chunks_metadata)}")

        except Exception as e:
            logger.error(f"Failed to load RAG store: {str(e)}")
            raise ClaudeAPIError(f"Failed to load session data: {str(e)}")

        # Initialize analyzer for API calls
        self.analyzer = ComprehensiveAnalyzer(
            model_mode=model_mode,
            local_model_name=local_model_name
        )

        # Chat history
        self.chat_history: List[Dict] = []

    def ask_question(self, question: str, max_context_chunks: int = 5) -> Dict:
        """
        Ask a question about the documents using two-stage search:
        1. First search the generated summary PDF
        2. If insufficient information, search the original source PDFs

        Args:
            question: User's question
            max_context_chunks: Maximum number of context chunks to retrieve

        Returns:
            Dictionary with answer and sources
        """
        try:
            # Validate input to prevent prompt injection
            question = self._validate_question(question)

            logger.info(f"Processing question: {question[:100]}...")

            # Get summary PDF name from session metadata
            summary_pdf_name = self.session.metadata.get("summary_pdf_name", "")

            # Get list of source PDF names for filtering
            source_pdf_names = self.session.metadata.get("source_pdf_names", [])

            # STAGE 1: Search summary PDF first (if it exists)
            context = ""
            metadata_list = []
            search_stage = "sources"  # Default to sources if no summary

            if summary_pdf_name:
                logger.info(f"Stage 1: Searching summary PDF: {summary_pdf_name}...")

                # Use RAG system's search method to get chunks with scores
                search_results = self.rag_system.search(
                    question,
                    k=max_context_chunks * 2  # Get more to filter from
                )

                # Filter for summary PDF only
                summary_results = [
                    result for result in search_results
                    if summary_pdf_name in result["metadata"].get("doc_name", "")
                ]

                if len(summary_results) >= 3:
                    # Found enough in summary, use only summary results
                    logger.info(f"✓ Stage 1 found {len(summary_results)} chunks from summary PDF")
                    summary_results = summary_results[:max_context_chunks]

                    # Build context and metadata from filtered results
                    context_parts = []
                    metadata_list = []

                    for i, result in enumerate(summary_results):
                        text = result["text"]
                        meta = result["metadata"]
                        source = meta.get("source", f"{meta.get('doc_name')}, p.{meta.get('page')}")
                        section = meta.get("section", "Unknown Section")

                        context_part = f"[Source {i+1}: {source}, §{section}]\n{text}\n"
                        context_parts.append(context_part)
                        metadata_list.append(meta)

                    context = "\n".join(context_parts)
                    search_stage = "summary"
                else:
                    logger.info(f"Stage 1 found only {len(summary_results)} chunks from summary. Proceeding to Stage 2...")

            # STAGE 2: If insufficient information in summary, search source PDFs
            if len(metadata_list) < 3:
                logger.info("Stage 2: Searching all documents (source PDFs)...")
                context, metadata_list = self.rag_system.get_relevant_context(
                    question,
                    max_chunks=max_context_chunks
                )
                search_stage = "sources"
                logger.info(f"✓ Stage 2 found {len(metadata_list)} chunks from all documents")

            if not context:
                return {
                    "answer": "I couldn't find relevant information in the documents to answer your question. The question may be outside the scope of the provided documents.",
                    "sources": [],
                    "context_found": False,
                    "search_stage": "none"
                }

            # Build prompt for LLM with STRICT document grounding
            system_prompt = """You are an expert research assistant helping users understand academic papers.

CRITICAL INSTRUCTIONS:
- Answer ONLY using the provided context from research documents
- DO NOT use your general knowledge or training data
- If the context doesn't contain the answer, explicitly say "The provided documents do not contain information about this"
- Never make assumptions or inferences beyond what's explicitly stated in the context
- Every claim must be supported by the provided context

Guidelines:
- Provide clear, detailed answers in 2-3 paragraphs
- Reference specific sources with page numbers
- Use natural, flowing language (not bullet points)
- Include relevant details, data, and findings from the context
- Be precise and accurate
"""

            # Format context with sources
            formatted_context = self._format_context_with_sources(context, metadata_list)

            # Create user prompt
            user_prompt = f"""Based on the following excerpts from research documents, please answer this question:

**Question**: {question}

**Context from Documents**:
{formatted_context}

**STRICT INSTRUCTIONS**:
- Answer ONLY using the provided context above
- DO NOT use any external knowledge or general AI knowledge
- If the context doesn't contain enough information, clearly state: "The provided documents do not contain sufficient information about [specific aspect]"
- Reference specific documents and page numbers when making claims
- Write in clear, professional paragraphs (not bullet points)
"""

            # Get answer from LLM
            answer = self._generate_answer(system_prompt, user_prompt)

            # Extract unique sources
            sources = self._extract_unique_sources(metadata_list)

            # Store in chat history
            self.chat_history.append({
                "question": question,
                "answer": answer,
                "sources": sources,
                "search_stage": search_stage
            })

            return {
                "answer": answer,
                "sources": sources,
                "context_found": True,
                "search_stage": search_stage
            }

        except Exception as e:
            logger.error(f"Failed to answer question: {str(e)}")
            return {
                "answer": f"Error processing question: {str(e)}",
                "sources": [],
                "context_found": False,
                "search_stage": "error"
            }

    def _validate_question(self, question: str) -> str:
        """
        Validate and sanitize user question to prevent prompt injection

        Args:
            question: User's question

        Returns:
            Sanitized question

        Raises:
            ValueError: If question is invalid
        """
        # Check length
        if len(question) > 2000:
            raise ValueError("Question too long (max 2000 characters)")

        # Check minimum length
        if len(question.strip()) < 3:
            raise ValueError("Question too short (min 3 characters)")

        # Strip whitespace
        question = question.strip()

        # Log suspicious patterns (but don't block - Claude has built-in safety)
        suspicious_patterns = [
            "ignore previous", "ignore all previous", "ignore instructions",
            "disregard", "bypass", "override system", "act as", "pretend to be",
            "forget everything", "new instructions"
        ]

        question_lower = question.lower()
        for pattern in suspicious_patterns:
            if pattern in question_lower:
                logger.warning(f"Suspicious prompt pattern detected: {pattern}")
                # Don't block - just log for monitoring

        return question

    def _format_context_with_sources(self, context: str, metadata_list: List[Dict]) -> str:
        """Format context with source attribution"""
        # Context already formatted by RAG system with sources
        return context

    def _extract_unique_sources(self, metadata_list: List[Dict]) -> List[Dict]:
        """Extract unique sources from metadata"""
        seen = set()
        unique_sources = []

        for metadata in metadata_list:
            doc_name = metadata.get("doc_name", "Unknown")
            page = metadata.get("page", 0)
            section = metadata.get("section", "Unknown Section")

            source_key = f"{doc_name}_{page}"
            if source_key not in seen:
                seen.add(source_key)
                unique_sources.append({
                    "doc_name": doc_name,
                    "page": page,
                    "section": section,
                    "source": metadata.get("source", f"{doc_name}, p.{page}")
                })

        return unique_sources

    def _generate_answer(self, system_prompt: str, user_prompt: str) -> str:
        """Generate answer using LLM"""
        try:
            messages = [
                {"role": "user", "content": user_prompt}
            ]

            # Use analyzer to make API call
            answer = self.analyzer._make_api_call_with_retry(
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=2000
            )

            return answer

        except Exception as e:
            logger.error(f"Failed to generate answer: {str(e)}")
            raise ClaudeAPIError(f"Failed to generate answer: {str(e)}")

    def get_chat_history(self) -> List[Dict]:
        """Get full chat history"""
        return self.chat_history

    def clear_history(self):
        """Clear chat history"""
        self.chat_history = []
        logger.info("Chat history cleared")

    def get_session_info(self) -> Dict:
        """Get information about the current session"""
        return {
            "session_id": self.session.session_id,
            "session_name": self.session.session_name,
            "source_pdf_count": self.session.metadata["source_pdf_count"],
            "has_summary": self.session.metadata["has_summary"],
            "total_pages": self.session.metadata.get("total_pages", 0),
            "total_images": self.session.metadata.get("total_images", 0),
            "source_pdf_names": self.session.metadata.get("source_pdf_names", [])
        }
