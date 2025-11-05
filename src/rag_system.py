"""
RAG (Retrieval-Augmented Generation) System
Handles document chunking, embedding, and semantic search
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pickle
import json

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from config.settings import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_MODEL,
    EMBEDDING_CACHE_FOLDER,
    TOP_K_RETRIEVAL,
    SIMILARITY_THRESHOLD,
    BASE_DIR
)
from utils.logger import get_logger
from utils.exceptions import RAGSystemError, VectorStoreError, EmbeddingError
from src.hybrid_retrieval import HybridRetriever

logger = get_logger(__name__)


class RAGSystem:
    """
    Retrieval-Augmented Generation system for document analysis
    """

    def __init__(self):
        """Initialize RAG system"""
        self.embeddings = None
        self.vector_store = None
        self.text_splitter = None
        self.documents = []
        self.chunks_metadata = []
        self.hybrid_retriever = None  # Hybrid retrieval with BM25 + Vector + Reranking

        self._initialize_components()

    def _initialize_components(self):
        """Initialize embeddings and text splitter"""
        try:
            logger.info("Initializing RAG system components...")

            # Initialize embeddings with caching for faster subsequent loads
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            EMBEDDING_CACHE_FOLDER.mkdir(parents=True, exist_ok=True)  # Ensure cache directory exists
            self.embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL,
                cache_folder=str(EMBEDDING_CACHE_FOLDER),  # Cache models for faster loading
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            logger.info("✓ Embedding model loaded (cached for faster subsequent loads)")

            # Initialize text splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
                length_function=len,
                separators=["\n\n", "\n", ". ", "! ", "? ", ", ", " ", ""]
            )

            # Initialize hybrid retriever (BM25 + Vector + Reranking)
            logger.info("Initializing Hybrid Retriever with cross-encoder...")
            self.hybrid_retriever = HybridRetriever()

            logger.info("RAG system components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize RAG components: {str(e)}")
            raise RAGSystemError(f"Initialization failed: {str(e)}")

    def process_documents(self, pdf_data_list: List[Dict]) -> int:
        """
        Process PDF documents and create vector store

        Args:
            pdf_data_list: List of PDF data dictionaries from PDFProcessor

        Returns:
            Number of chunks created

        Raises:
            RAGSystemError: If processing fails
        """
        try:
            logger.info(f"Processing {len(pdf_data_list)} documents for RAG system")

            all_chunks = []
            self.chunks_metadata = []

            for doc_id, pdf_data in enumerate(pdf_data_list):
                doc_name = pdf_data.get("doc_name", f"Document_{doc_id}")
                pages = pdf_data.get("pages", [])

                logger.info(f"Processing document: {doc_name} ({len(pages)} pages)")

                # Track chunks created for this document
                doc_chunk_count = 0

                for page_data in pages:
                    page_num = page_data.get("page_num", 0)
                    text = page_data.get("text", "")
                    section = page_data.get("section", "Unknown Section")
                    images = page_data.get("images", [])

                    if not text or len(text.strip()) < 50:
                        logger.debug(f"Skipping page {page_num} (insufficient text)")
                        continue

                    # Split text into chunks
                    page_chunks = self.text_splitter.split_text(text)

                    for chunk_id, chunk_text in enumerate(page_chunks):
                        if len(chunk_text.strip()) < 30:
                            continue

                        # Create metadata for chunk
                        metadata = {
                            "doc_id": doc_id,
                            "doc_name": doc_name,
                            "page": page_num,
                            "chunk_id": chunk_id,
                            "section": section,
                            "has_images": len(images) > 0,
                            "image_count": len(images),
                            "source": f"{doc_name}, p.{page_num}"
                        }

                        # Store images metadata
                        if images:
                            metadata["images"] = [
                                {
                                    "path": str(img.get("image_path")),
                                    "format": img.get("format"),
                                    "page": img.get("page"),
                                    "index": img.get("index")
                                }
                                for img in images
                            ]

                        # Create LangChain Document
                        doc = Document(
                            page_content=chunk_text,
                            metadata=metadata
                        )

                        all_chunks.append(doc)
                        self.chunks_metadata.append(metadata)
                        doc_chunk_count += 1

                logger.info(f"Created {doc_chunk_count} chunks from {doc_name}")

            if not all_chunks:
                raise RAGSystemError("No valid chunks created from documents")

            # Create vector store
            logger.info(f"Creating vector store with {len(all_chunks)} chunks...")
            self.vector_store = FAISS.from_documents(all_chunks, self.embeddings)

            self.documents = pdf_data_list
            logger.info(f"Vector store created successfully with {len(all_chunks)} chunks")

            # Build BM25 index for hybrid retrieval
            if self.hybrid_retriever:
                logger.info("Building BM25 index for hybrid retrieval...")
                chunk_texts = [doc.page_content for doc in all_chunks]
                self.hybrid_retriever.build_bm25_index(chunk_texts)
                logger.info("✓ BM25 index built successfully")

            return len(all_chunks)

        except Exception as e:
            logger.error(f"Failed to process documents: {str(e)}")
            raise RAGSystemError(f"Document processing failed: {str(e)}")

    def search(self, query: str, k: int = TOP_K_RETRIEVAL, filter_dict: Optional[Dict] = None) -> List[Dict]:
        """
        Search vector store for relevant chunks

        Args:
            query: Search query
            k: Number of results to return
            filter_dict: Optional metadata filters (e.g., {"doc_name": "summary.pdf"})

        Returns:
            List of dictionaries with chunks and metadata

        Raises:
            VectorStoreError: If search fails
        """
        try:
            if not self.vector_store:
                raise VectorStoreError("Vector store not initialized. Process documents first.")

            logger.debug(f"Searching for: '{query[:50]}...' (k={k}, filter={filter_dict})")

            # Perform similarity search with scores
            results = self.vector_store.similarity_search_with_score(query, k=k)

            formatted_results = []
            for doc, score in results:
                # Convert score to similarity (FAISS returns distance)
                similarity = 1 / (1 + score)

                if similarity < SIMILARITY_THRESHOLD:
                    continue

                # Apply metadata filters if provided
                if filter_dict:
                    metadata = doc.metadata
                    matches = all(
                        metadata.get(key) == value
                        for key, value in filter_dict.items()
                    )
                    if not matches:
                        continue

                result = {
                    "text": doc.page_content,
                    "metadata": doc.metadata,
                    "similarity": similarity,
                    "score": score
                }

                formatted_results.append(result)

            logger.debug(f"Found {len(formatted_results)} relevant chunks")
            return formatted_results

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise VectorStoreError(f"Search failed: {str(e)}")

    def hybrid_search(self, query: str, k: int = 5, retrieve_k: int = 20) -> List[Dict]:
        """
        Perform hybrid search (BM25 + Vector) with cross-encoder reranking

        Args:
            query: Search query
            k: Final number of results after reranking (default: 5)
            retrieve_k: Number of candidates for reranking (default: 20)

        Returns:
            List of dictionaries with reranked chunks and metadata
        """
        try:
            if not self.vector_store or not self.hybrid_retriever:
                logger.warning("Hybrid retrieval not available, falling back to vector search")
                return self.search(query, k=k)

            logger.debug(f"🔍 Hybrid search: query='{query[:50]}...', k={k}, retrieve_k={retrieve_k}")

            # Step 1: Get initial vector search candidates (top 20-30 for reranking)
            vector_results = self.vector_store.similarity_search_with_score(query, k=retrieve_k)

            # Format vector results for hybrid retriever
            formatted_vector_results = []
            for doc, score in vector_results:
                # Convert FAISS distance to similarity
                similarity = 1 / (1 + score)
                formatted_vector_results.append((doc.page_content, similarity, doc.metadata))

            # Step 2: Hybrid search (BM25 + Vector fusion) → top retrieve_k
            # Step 3: Cross-encoder reranking → top k
            if self.hybrid_retriever:
                final_results = self.hybrid_retriever.retrieve_with_hybrid_and_rerank(
                    query=query,
                    vector_results=formatted_vector_results,
                    retrieve_k=retrieve_k,
                    final_k=k
                )

                # Format results
                formatted_results = []
                for text, rerank_score, metadata in final_results:
                    result = {
                        "text": text,
                        "metadata": metadata,
                        "similarity": rerank_score,  # Using rerank score as similarity
                        "score": 1 - rerank_score  # For compatibility
                    }
                    formatted_results.append(result)

                logger.info(f"✓ Hybrid search complete: {len(formatted_results)} results")
                return formatted_results

            else:
                # Fallback if hybrid retriever not initialized
                logger.warning("Hybrid retriever not initialized, using vector search only")
                return self.search(query, k=k)

        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}, falling back to vector search")
            return self.search(query, k=k)

    def add_documents(self, pdf_data_list: List[Dict]) -> int:
        """
        Add new documents to existing vector store (APPEND, not replace)

        This method is critical for adding summary PDFs to sessions that already
        contain source PDFs in the RAG system.

        Args:
            pdf_data_list: List of PDF data dictionaries from PDFProcessor

        Returns:
            Number of NEW chunks created (not total)

        Raises:
            RAGSystemError: If adding documents fails
        """
        try:
            if not self.vector_store:
                raise RAGSystemError("Cannot add documents - vector store not initialized. Use process_documents() first.")

            logger.info(f"Adding {len(pdf_data_list)} new documents to existing RAG system...")

            # Track current state
            chunks_before = len(self.chunks_metadata)
            doc_id_offset = len(self.documents)  # Continue doc_id sequence

            all_new_chunks = []
            new_chunks_metadata = []

            for idx, pdf_data in enumerate(pdf_data_list):
                doc_id = doc_id_offset + idx
                doc_name = pdf_data.get("doc_name", f"Document_{doc_id}")
                pages = pdf_data.get("pages", [])

                logger.info(f"Adding document: {doc_name} ({len(pages)} pages)")

                doc_chunk_count = 0

                for page_data in pages:
                    page_num = page_data.get("page_num", 0)
                    text = page_data.get("text", "")
                    section = page_data.get("section", "Unknown Section")
                    images = page_data.get("images", [])

                    if not text or len(text.strip()) < 50:
                        logger.debug(f"Skipping page {page_num} (insufficient text)")
                        continue

                    # Split text into chunks
                    page_chunks = self.text_splitter.split_text(text)

                    for chunk_id, chunk_text in enumerate(page_chunks):
                        if len(chunk_text.strip()) < 30:
                            continue

                        # Create metadata for chunk
                        metadata = {
                            "doc_id": doc_id,
                            "doc_name": doc_name,
                            "page": page_num,
                            "chunk_id": chunk_id,
                            "section": section,
                            "has_images": len(images) > 0,
                            "image_count": len(images),
                            "source": f"{doc_name}, p.{page_num}"
                        }

                        # Store images metadata
                        if images:
                            metadata["images"] = [
                                {
                                    "path": str(img.get("image_path")),
                                    "format": img.get("format"),
                                    "page": img.get("page"),
                                    "index": img.get("index")
                                }
                                for img in images
                            ]

                        # Create LangChain Document
                        doc = Document(
                            page_content=chunk_text,
                            metadata=metadata
                        )

                        all_new_chunks.append(doc)
                        new_chunks_metadata.append(metadata)
                        doc_chunk_count += 1

                logger.info(f"Created {doc_chunk_count} new chunks from {doc_name}")

            if not all_new_chunks:
                logger.warning("No valid chunks created from new documents")
                return 0

            # Add new documents to existing vector store
            logger.info(f"Adding {len(all_new_chunks)} new chunks to vector store...")
            self.vector_store.add_documents(all_new_chunks)

            # Append metadata and documents
            self.chunks_metadata.extend(new_chunks_metadata)
            self.documents.extend(pdf_data_list)

            chunks_after = len(self.chunks_metadata)
            logger.info(f"✓ Added {len(all_new_chunks)} new chunks (total: {chunks_before} → {chunks_after})")

            # Rebuild BM25 index with ALL documents (old + new)
            if self.hybrid_retriever:
                logger.info("Rebuilding BM25 index with all documents...")
                # Get all chunk texts from vector store
                all_chunk_texts = [metadata["source"] for metadata in self.chunks_metadata]
                # Reconstruct texts from stored documents
                all_texts = []
                for doc_data in self.documents:
                    for page in doc_data.get("pages", []):
                        text = page.get("text", "")
                        if text:
                            all_texts.append(text)

                if all_texts:
                    self.hybrid_retriever.build_bm25_index(all_texts)
                    logger.info("✓ BM25 index rebuilt successfully with all documents")

            return len(all_new_chunks)

        except Exception as e:
            logger.error(f"Failed to add documents: {str(e)}")
            raise RAGSystemError(f"Adding documents failed: {str(e)}")

    def get_relevant_context(self, query: str, max_chunks: int = 5, filter_dict: Optional[Dict] = None) -> Tuple[str, List[Dict]]:
        """
        Get relevant context for a query using hybrid retrieval

        Args:
            query: Search query
            max_chunks: Maximum number of chunks to retrieve
            filter_dict: Optional metadata filters (e.g., {"doc_name": "summary.pdf"})

        Returns:
            Tuple of (combined_context, metadata_list)
        """
        try:
            # Use hybrid search if available, otherwise fall back to regular search
            if self.hybrid_retriever and self.hybrid_retriever.bm25 is not None:
                logger.info(f"🔍 Using Hybrid Retrieval (BM25 + Vector + Reranking)")
                results = self.hybrid_search(query, k=max_chunks, retrieve_k=20)
            else:
                logger.info(f"🔍 Using Vector Search only")
                results = self.search(query, k=max_chunks, filter_dict=filter_dict)

            if not results:
                return "", []

            # Combine text from chunks
            context_parts = []
            metadata_list = []

            for i, result in enumerate(results):
                text = result["text"]
                metadata = result["metadata"]
                similarity = result["similarity"]

                # Add source information
                source = metadata.get("source", "Unknown")
                section = metadata.get("section", "Unknown Section")

                context_part = f"[Source {i+1}: {source}, §{section}]\n{text}\n"
                context_parts.append(context_part)
                metadata_list.append(metadata)

            combined_context = "\n".join(context_parts)

            logger.debug(f"Retrieved {len(results)} chunks for context")
            return combined_context, metadata_list

        except Exception as e:
            logger.error(f"Failed to get relevant context: {str(e)}")
            return "", []

    def get_chunks_by_document(self, doc_id: int) -> List[Dict]:
        """
        Get all chunks for a specific document

        Args:
            doc_id: Document ID

        Returns:
            List of chunk dictionaries
        """
        return [
            chunk for chunk in self.chunks_metadata
            if chunk.get("doc_id") == doc_id
        ]

    def get_chunks_by_page(self, doc_id: int, page_num: int) -> List[Dict]:
        """
        Get all chunks for a specific page

        Args:
            doc_id: Document ID
            page_num: Page number

        Returns:
            List of chunk dictionaries
        """
        return [
            chunk for chunk in self.chunks_metadata
            if chunk.get("doc_id") == doc_id and chunk.get("page") == page_num
        ]

    def _make_json_serializable(self, obj):
        """
        Convert objects to JSON-serializable format

        Handles PIL Images, Path objects, and other non-serializable types
        """
        from PIL import Image

        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, Image.Image):
            # PIL Image objects - just skip them (we already have paths)
            return None
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            # For any other non-serializable object, convert to string
            try:
                return str(obj)
            except:
                return None

    def save_vector_store(self, path: Path):
        """
        Save vector store to disk

        Args:
            path: Path to save directory

        Raises:
            VectorStoreError: If save fails
        """
        try:
            if not self.vector_store:
                raise VectorStoreError("No vector store to save")

            path.mkdir(parents=True, exist_ok=True)

            # Save FAISS index
            faiss_path = path / "faiss_index"
            self.vector_store.save_local(str(faiss_path))

            # Make data JSON-serializable (removes PIL Images, converts Paths to strings)
            serializable_metadata = self._make_json_serializable(self.chunks_metadata)
            serializable_documents = self._make_json_serializable(self.documents)

            # Save metadata (using JSON for security)
            metadata_path = path / "chunks_metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(serializable_metadata, f, indent=2)

            # Save documents (using JSON for security)
            docs_path = path / "documents.json"
            with open(docs_path, "w") as f:
                json.dump(serializable_documents, f, indent=2)

            logger.info(f"Vector store saved to {path}")

        except Exception as e:
            logger.error(f"Failed to save vector store: {str(e)}")
            raise VectorStoreError(f"Save failed: {str(e)}")

    def load_vector_store(self, path: Path):
        """
        Load vector store from disk

        Args:
            path: Path to saved directory

        Raises:
            VectorStoreError: If load fails
        """
        try:
            # Load FAISS index
            faiss_path = path / "faiss_index"
            self.vector_store = FAISS.load_local(
                str(faiss_path),
                self.embeddings,
                allow_dangerous_deserialization=True
            )

            # Load metadata (try JSON first, fallback to pickle for old sessions)
            metadata_path_json = path / "chunks_metadata.json"
            metadata_path_pkl = path / "chunks_metadata.pkl"

            if metadata_path_json.exists():
                with open(metadata_path_json, "r") as f:
                    self.chunks_metadata = json.load(f)
            elif metadata_path_pkl.exists():
                logger.warning("Loading from legacy pickle format - will upgrade on next save")
                with open(metadata_path_pkl, "rb") as f:
                    self.chunks_metadata = pickle.load(f)
            else:
                raise FileNotFoundError("Metadata file not found")

            # Load documents (try JSON first, fallback to pickle for old sessions)
            docs_path_json = path / "documents.json"
            docs_path_pkl = path / "documents.pkl"

            if docs_path_json.exists():
                with open(docs_path_json, "r") as f:
                    self.documents = json.load(f)
            elif docs_path_pkl.exists():
                logger.warning("Loading from legacy pickle format - will upgrade on next save")
                with open(docs_path_pkl, "rb") as f:
                    self.documents = pickle.load(f)
            else:
                raise FileNotFoundError("Documents file not found")

            logger.info(f"Vector store loaded from {path}")

        except Exception as e:
            logger.error(f"Failed to load vector store: {str(e)}")
            raise VectorStoreError(f"Load failed: {str(e)}")

    def get_statistics(self) -> Dict:
        """
        Get statistics about the RAG system

        Returns:
            Dictionary with statistics
        """
        return {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks_metadata),
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "embedding_model": EMBEDDING_MODEL,
            "has_vector_store": self.vector_store is not None
        }
