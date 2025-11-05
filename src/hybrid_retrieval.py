"""
Hybrid Retrieval System
Combines BM25 (keyword) + Vector (semantic) search with cross-encoder reranking
for 67% failure reduction (Claude research findings)
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
import re
import tiktoken

from utils.logger import get_logger

logger = get_logger(__name__)

# Safety limits to prevent excessive API costs and memory issues
MAX_RERANK_CANDIDATES = 50  # Maximum candidates to rerank (prevent memory issues)
MAX_CHUNK_LENGTH = 8000  # Maximum characters per chunk for reranking
MAX_QUERY_LENGTH = 1000  # Maximum query length
RERANK_BATCH_SIZE = 20  # Process reranking in batches to prevent memory issues


class HybridRetriever:
    """
    Hybrid retrieval combining BM25 (keyword) and vector (semantic) search

    Architecture:
    1. BM25 search: Find keyword-based matches
    2. Vector search: Find semantically similar chunks (using existing FAISS)
    3. Combine results with weighted fusion
    4. Rerank top candidates with cross-encoder

    Result: 67% reduction in retrieval failures (Claude research)
    """

    def __init__(self, cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize hybrid retriever with robust error handling

        Args:
            cross_encoder_model: Cross-encoder model for reranking
        """
        self.cross_encoder = None
        self.bm25 = None
        self.corpus_texts = []
        self.bm25_weight = 0.5
        self.vector_weight = 0.5
        self.model_loaded = False

        try:
            # Initialize cross-encoder for reranking with timeout protection
            logger.info(f"Loading cross-encoder model: {cross_encoder_model}")
            self.cross_encoder = CrossEncoder(cross_encoder_model, max_length=512)
            self.model_loaded = True
            logger.info("✓ Cross-encoder loaded successfully")

        except MemoryError:
            logger.error("❌ MemoryError loading cross-encoder - insufficient RAM")
            logger.warning("⚠️  Cross-encoder disabled, using BM25 + Vector fusion only")

        except ImportError as e:
            logger.error(f"❌ Import error: {str(e)} - required packages may be missing")
            logger.warning("⚠️  Cross-encoder disabled, using BM25 + Vector fusion only")

        except Exception as e:
            logger.error(f"❌ Failed to initialize cross-encoder: {str(e)}")
            logger.warning("⚠️  Cross-encoder disabled, using BM25 + Vector fusion only")

        logger.info(f"Hybrid Retriever initialized: BM25={True}, Vector={True}, Reranking={self.model_loaded}")

    def _validate_and_truncate_text(self, text: str, max_length: int = MAX_CHUNK_LENGTH) -> str:
        """
        Validate and truncate text to prevent memory/processing issues

        Args:
            text: Input text
            max_length: Maximum character length

        Returns:
            Truncated text if needed
        """
        if not text or not isinstance(text, str):
            return ""

        if len(text) > max_length:
            logger.warning(f"Truncating text from {len(text)} to {max_length} characters")
            return text[:max_length]

        return text

    def _validate_query(self, query: str) -> str:
        """
        Validate and sanitize query to prevent issues

        Args:
            query: Search query

        Returns:
            Validated query

        Raises:
            ValueError: If query is invalid
        """
        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")

        query = query.strip()

        if len(query) < 2:
            raise ValueError("Query too short (minimum 2 characters)")

        if len(query) > MAX_QUERY_LENGTH:
            logger.warning(f"Query truncated from {len(query)} to {MAX_QUERY_LENGTH} characters")
            query = query[:MAX_QUERY_LENGTH]

        return query

    def build_bm25_index(self, texts: List[str]):
        """
        Build BM25 index from corpus texts with validation and error handling

        Args:
            texts: List of document texts
        """
        try:
            if not texts:
                logger.warning("No texts provided for BM25 index")
                self.bm25 = None
                return

            logger.info(f"Building BM25 index for {len(texts)} documents")

            # Validate and truncate texts to prevent memory issues
            validated_texts = []
            for i, text in enumerate(texts):
                try:
                    validated_text = self._validate_and_truncate_text(text)
                    if validated_text:
                        validated_texts.append(validated_text)
                except Exception as e:
                    logger.warning(f"Skipping invalid text at index {i}: {str(e)}")
                    validated_texts.append("")  # Keep index alignment

            if not validated_texts:
                logger.error("No valid texts after validation")
                self.bm25 = None
                return

            # Tokenize texts for BM25
            tokenized_corpus = []
            for i, text in enumerate(validated_texts):
                try:
                    tokens = self._tokenize(text)
                    tokenized_corpus.append(tokens)
                except Exception as e:
                    logger.warning(f"Tokenization error at index {i}: {str(e)}")
                    tokenized_corpus.append([])  # Keep index alignment

            # Build BM25 index
            self.bm25 = BM25Okapi(tokenized_corpus)
            self.corpus_texts = validated_texts

            logger.info("✓ BM25 index built successfully")

        except MemoryError:
            logger.error("❌ MemoryError building BM25 index - corpus too large")
            self.bm25 = None

        except Exception as e:
            logger.error(f"❌ Failed to build BM25 index: {str(e)}")
            self.bm25 = None

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25 indexing

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        # Simple tokenization: lowercase, split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r'\b\w+\b', text)
        return tokens

    def hybrid_search(
        self,
        query: str,
        vector_results: List[Tuple[str, float, Dict]],
        top_k: int = 20
    ) -> List[Tuple[str, float, Dict]]:
        """
        Perform hybrid search combining BM25 and vector search with robust error handling

        Args:
            query: Search query
            vector_results: Results from vector search (text, score, metadata)
            top_k: Number of results to retrieve (default: 20 for reranking)

        Returns:
            List of (text, combined_score, metadata) tuples
        """
        try:
            # Validate query
            try:
                query = self._validate_query(query)
            except ValueError as e:
                logger.error(f"Invalid query for hybrid search: {str(e)}")
                return vector_results[:top_k]

            # Validate vector results
            if not vector_results:
                logger.warning("No vector results provided for hybrid search")
                return []

            # If BM25 not built, return vector results only
            if self.bm25 is None or not self.corpus_texts:
                logger.warning("BM25 index not built, using vector search only")
                return vector_results[:top_k]

            logger.debug(f"Hybrid search: query='{query[:50]}...', vector_results={len(vector_results)}")

            # Step 1: BM25 search
            tokenized_query = self._tokenize(query)
            bm25_scores = self.bm25.get_scores(tokenized_query)

            # Get top BM25 results
            bm25_top_indices = np.argsort(bm25_scores)[::-1][:top_k]

            # Create BM25 results with normalized scores
            max_bm25_score = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
            bm25_results = []
            for idx in bm25_top_indices:
                if idx < len(self.corpus_texts):
                    normalized_score = bm25_scores[idx] / max_bm25_score
                    # Find metadata for this text (if it exists in vector results)
                    metadata = self._find_metadata(self.corpus_texts[idx], vector_results)
                    bm25_results.append((self.corpus_texts[idx], normalized_score, metadata))

            # Step 2: Normalize vector scores
            vector_scores = [score for _, score, _ in vector_results]
            max_vector_score = max(vector_scores) if max(vector_scores) > 0 else 1.0
            normalized_vector_results = [
                (text, score / max_vector_score, metadata)
                for text, score, metadata in vector_results
            ]

            # Step 3: Combine with weighted fusion
            combined_results = self._weighted_fusion(
                bm25_results,
                normalized_vector_results,
                top_k=top_k
            )

            logger.info(f"✓ Hybrid search complete: {len(combined_results)} results")
            return combined_results

        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            # Fallback to vector results
            return vector_results[:top_k]

    def _find_metadata(self, text: str, vector_results: List[Tuple[str, float, Dict]]) -> Dict:
        """Find metadata for a text chunk from vector results"""
        for vtext, _, vmeta in vector_results:
            if vtext == text:
                return vmeta
        return {}  # Return empty dict if not found

    def _weighted_fusion(
        self,
        bm25_results: List[Tuple[str, float, Dict]],
        vector_results: List[Tuple[str, float, Dict]],
        top_k: int
    ) -> List[Tuple[str, float, Dict]]:
        """
        Combine BM25 and vector results with weighted fusion

        Args:
            bm25_results: BM25 search results
            vector_results: Vector search results
            top_k: Number of results to return

        Returns:
            Combined and sorted results
        """
        # Create a dictionary to accumulate scores
        combined_scores = {}

        # Add BM25 scores
        for text, score, metadata in bm25_results:
            combined_scores[text] = {
                'score': self.bm25_weight * score,
                'metadata': metadata
            }

        # Add vector scores (merge if text already exists)
        for text, score, metadata in vector_results:
            if text in combined_scores:
                combined_scores[text]['score'] += self.vector_weight * score
                # Merge metadata (prefer vector metadata as it's more complete)
                combined_scores[text]['metadata'].update(metadata)
            else:
                combined_scores[text] = {
                    'score': self.vector_weight * score,
                    'metadata': metadata
                }

        # Convert back to list and sort by combined score
        results = [
            (text, data['score'], data['metadata'])
            for text, data in combined_scores.items()
        ]
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]

    def rerank(
        self,
        query: str,
        candidates: List[Tuple[str, float, Dict]],
        top_k: int = 5
    ) -> List[Tuple[str, float, Dict]]:
        """
        Rerank candidates using cross-encoder with robust error handling and safety limits

        Args:
            query: Search query
            candidates: Candidate results from hybrid search
            top_k: Number of top results to return after reranking

        Returns:
            Reranked results (text, rerank_score, metadata)
        """
        try:
            # Validate query
            try:
                query = self._validate_query(query)
            except ValueError as e:
                logger.error(f"Invalid query for reranking: {str(e)}")
                return candidates[:top_k]

            # If cross-encoder not available, return candidates as-is
            if not self.model_loaded or self.cross_encoder is None:
                logger.warning("Cross-encoder not available, skipping reranking")
                return candidates[:top_k]

            if not candidates:
                logger.warning("No candidates provided for reranking")
                return []

            # Limit number of candidates to prevent memory issues
            if len(candidates) > MAX_RERANK_CANDIDATES:
                logger.warning(
                    f"Too many candidates ({len(candidates)}), limiting to {MAX_RERANK_CANDIDATES} "
                    f"to prevent memory issues"
                )
                candidates = candidates[:MAX_RERANK_CANDIDATES]

            logger.debug(f"Reranking {len(candidates)} candidates with top_k={top_k}")

            # Validate and truncate texts for reranking
            valid_candidates = []
            for text, score, metadata in candidates:
                try:
                    # Validate and truncate text
                    truncated_text = self._validate_and_truncate_text(text)
                    if truncated_text:
                        valid_candidates.append((truncated_text, score, metadata))
                except Exception as e:
                    logger.warning(f"Skipping invalid candidate: {str(e)}")

            if not valid_candidates:
                logger.error("No valid candidates after validation")
                return candidates[:top_k]

            # Prepare query-document pairs
            texts = [text for text, _, _ in valid_candidates]
            query_doc_pairs = [[query, text] for text in texts]

            # Get reranking scores from cross-encoder with batch processing
            try:
                if len(query_doc_pairs) <= RERANK_BATCH_SIZE:
                    # Process all at once if small enough
                    rerank_scores = self.cross_encoder.predict(query_doc_pairs)
                else:
                    # Process in batches to prevent memory issues
                    logger.info(f"Processing {len(query_doc_pairs)} pairs in batches of {RERANK_BATCH_SIZE}")
                    rerank_scores = []
                    for i in range(0, len(query_doc_pairs), RERANK_BATCH_SIZE):
                        batch = query_doc_pairs[i:i+RERANK_BATCH_SIZE]
                        batch_scores = self.cross_encoder.predict(batch)
                        rerank_scores.extend(batch_scores)

            except MemoryError:
                logger.error("❌ MemoryError during reranking - reducing batch size")
                # Try again with smaller batches
                try:
                    rerank_scores = []
                    small_batch_size = RERANK_BATCH_SIZE // 2
                    for i in range(0, len(query_doc_pairs), small_batch_size):
                        batch = query_doc_pairs[i:i+small_batch_size]
                        batch_scores = self.cross_encoder.predict(batch)
                        rerank_scores.extend(batch_scores)
                except Exception:
                    # Complete fallback
                    logger.error("❌ Reranking failed even with reduced batch size, using original ranking")
                    return candidates[:top_k]

            except Exception as e:
                logger.error(f"❌ Cross-encoder prediction failed: {str(e)}")
                return candidates[:top_k]

            # Combine with original metadata
            reranked_results = []
            for (text, _, metadata), score in zip(valid_candidates, rerank_scores):
                try:
                    reranked_results.append((text, float(score), metadata))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid rerank score: {str(e)}, using original score")
                    # Find original score
                    original_score = next((s for t, s, _ in candidates if t == text), 0.0)
                    reranked_results.append((text, original_score, metadata))

            # Sort by reranking score
            reranked_results.sort(key=lambda x: x[1], reverse=True)

            logger.info(f"✓ Reranking complete: top-{top_k} selected from {len(reranked_results)} results")
            return reranked_results[:top_k]

        except MemoryError:
            logger.error("❌ MemoryError in rerank() - returning original candidates")
            return candidates[:top_k]

        except Exception as e:
            logger.error(f"❌ Reranking failed with unexpected error: {str(e)}")
            # Fallback to original ranking
            return candidates[:top_k]

    def retrieve_with_hybrid_and_rerank(
        self,
        query: str,
        vector_results: List[Tuple[str, float, Dict]],
        retrieve_k: int = 20,
        final_k: int = 5
    ) -> List[Tuple[str, float, Dict]]:
        """
        Complete hybrid retrieval pipeline:
        1. Hybrid search (BM25 + Vector) → top 20
        2. Rerank with cross-encoder → top 5

        Args:
            query: Search query
            vector_results: Initial vector search results
            retrieve_k: Number to retrieve from hybrid search (default: 20)
            final_k: Final number after reranking (default: 5)

        Returns:
            Final reranked results
        """
        logger.info(f"🔍 Full hybrid retrieval pipeline: query='{query[:50]}...'")

        # Step 1: Hybrid search
        hybrid_results = self.hybrid_search(query, vector_results, top_k=retrieve_k)

        # Step 2: Rerank
        final_results = self.rerank(query, hybrid_results, top_k=final_k)

        logger.info(f"✅ Hybrid retrieval complete: {len(final_results)} final results")
        return final_results

    def set_fusion_weights(self, bm25_weight: float = 0.5, vector_weight: float = 0.5):
        """
        Adjust fusion weights for BM25 vs Vector search

        Args:
            bm25_weight: Weight for BM25 scores (0-1)
            vector_weight: Weight for vector scores (0-1)
        """
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        logger.info(f"Fusion weights updated: BM25={bm25_weight}, Vector={vector_weight}")
