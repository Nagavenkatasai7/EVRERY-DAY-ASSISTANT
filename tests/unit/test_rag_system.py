"""
Unit Tests for RAG System
Tests document processing, vector search, and hybrid retrieval
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.rag_system import RAGSystem


class TestRAGSystemInitialization:
    """Test RAG system initialization"""

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_initialization_success(self, mock_embeddings):
        """Test successful initialization"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()

        assert rag.embeddings is not None
        assert rag.text_splitter is not None
        assert rag.documents == []
        assert rag.chunks_metadata == []

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_initialization_creates_cache_dir(self, mock_embeddings):
        """Test that cache directory is created"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()

        # Cache folder should exist after initialization
        from config.settings import EMBEDDING_CACHE_FOLDER
        assert EMBEDDING_CACHE_FOLDER.exists()


class TestDocumentProcessing:
    """Test document processing and chunking"""

    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_process_documents_success(self, mock_embeddings, mock_faiss, sample_pdf_data):
        """Test successful document processing"""
        mock_embeddings.return_value = Mock()
        mock_vector_store = Mock()
        mock_faiss.from_documents.return_value = mock_vector_store

        rag = RAGSystem()
        rag.hybrid_retriever = Mock()
        rag.hybrid_retriever.build_bm25_index = Mock()

        num_chunks = rag.process_documents([sample_pdf_data])

        assert num_chunks > 0
        assert len(rag.chunks_metadata) > 0
        assert rag.vector_store is not None
        mock_faiss.from_documents.assert_called_once()

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_process_documents_empty_list(self, mock_embeddings):
        """Test processing empty document list"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()

        with pytest.raises(Exception):  # Should raise RAGSystemError
            rag.process_documents([])

    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_process_documents_chunks_text(self, mock_embeddings, mock_faiss, sample_pdf_data):
        """Test that documents are properly chunked"""
        mock_embeddings.return_value = Mock()
        mock_faiss.from_documents.return_value = Mock()

        rag = RAGSystem()
        rag.hybrid_retriever = Mock()
        rag.hybrid_retriever.build_bm25_index = Mock()

        num_chunks = rag.process_documents([sample_pdf_data])

        # Should create multiple chunks from the text
        assert num_chunks >= 1
        # Chunks should have metadata
        assert all('doc_id' in chunk for chunk in rag.chunks_metadata)
        assert all('page' in chunk for chunk in rag.chunks_metadata)

    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_process_documents_skips_short_text(self, mock_embeddings, mock_faiss):
        """Test that very short text is skipped"""
        mock_embeddings.return_value = Mock()
        mock_faiss.from_documents.return_value = Mock()

        rag = RAGSystem()
        rag.hybrid_retriever = Mock()
        rag.hybrid_retriever.build_bm25_index = Mock()

        short_doc = {
            "doc_name": "short.pdf",
            "pages": [
                {"page_num": 1, "text": "Too short", "section": "Intro", "images": []}
            ]
        }

        with pytest.raises(Exception):  # Should raise due to insufficient text
            rag.process_documents([short_doc])

    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_process_documents_includes_images_metadata(self, mock_embeddings, mock_faiss, sample_pdf_data):
        """Test that image metadata is preserved"""
        mock_embeddings.return_value = Mock()
        mock_faiss.from_documents.return_value = Mock()

        rag = RAGSystem()
        rag.hybrid_retriever = Mock()
        rag.hybrid_retriever.build_bm25_index = Mock()

        rag.process_documents([sample_pdf_data])

        # Find chunks with images
        chunks_with_images = [c for c in rag.chunks_metadata if c.get('has_images')]

        assert len(chunks_with_images) > 0
        assert chunks_with_images[0]['image_count'] > 0


class TestVectorSearch:
    """Test vector similarity search"""

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_search_without_vector_store(self, mock_embeddings):
        """Test search fails without vector store"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()

        with pytest.raises(Exception):  # Should raise VectorStoreError
            rag.search("test query")

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_search_success(self, mock_embeddings, mock_vector_store):
        """Test successful vector search"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()
        rag.vector_store = mock_vector_store

        results = rag.search("test query", k=2)

        assert len(results) == 2
        assert all('text' in r for r in results)
        assert all('metadata' in r for r in results)
        assert all('similarity' in r for r in results)

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_search_with_filters(self, mock_embeddings, mock_vector_store):
        """Test search with metadata filters"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()
        rag.vector_store = mock_vector_store

        filter_dict = {"doc_name": "test.pdf"}
        results = rag.search("test query", k=2, filter_dict=filter_dict)

        # Should only return results matching filter
        assert all(r['metadata']['doc_name'] == 'test.pdf' for r in results)

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_search_similarity_threshold(self, mock_embeddings):
        """Test that similarity threshold is applied"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()

        # Mock vector store with low similarity results
        mock_vs = Mock()
        from langchain_core.documents import Document

        low_sim_doc = Document(
            page_content="Low similarity text",
            metadata={"doc_id": 0, "doc_name": "test.pdf"}
        )

        # High distance = low similarity
        mock_vs.similarity_search_with_score.return_value = [(low_sim_doc, 10.0)]
        rag.vector_store = mock_vs

        results = rag.search("test query", k=5)

        # Results with very low similarity should be filtered out
        assert len(results) == 0 or all(r['similarity'] > 0.01 for r in results)


class TestHybridSearch:
    """Test hybrid retrieval (BM25 + Vector + Reranking)"""

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_hybrid_search_fallback_to_vector(self, mock_embeddings, mock_vector_store):
        """Test fallback to vector search when hybrid not available"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()
        rag.vector_store = mock_vector_store
        rag.hybrid_retriever = None  # No hybrid retriever

        results = rag.hybrid_search("test query", k=2)

        # Should fallback to regular vector search
        assert len(results) == 2

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_hybrid_search_with_retriever(self, mock_embeddings, mock_vector_store):
        """Test hybrid search with retriever"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()
        rag.vector_store = mock_vector_store

        # Mock hybrid retriever
        mock_hybrid = Mock()
        mock_hybrid.bm25 = Mock()  # BM25 index exists
        mock_hybrid.retrieve_with_hybrid_and_rerank.return_value = [
            ("Result text 1", 0.95, {"doc_id": 0, "page": 1}),
            ("Result text 2", 0.88, {"doc_id": 0, "page": 2})
        ]
        rag.hybrid_retriever = mock_hybrid

        results = rag.hybrid_search("test query", k=2, retrieve_k=10)

        assert len(results) == 2
        assert results[0]['text'] == "Result text 1"
        assert results[0]['similarity'] == 0.95


class TestContextRetrieval:
    """Test relevant context retrieval"""

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_get_relevant_context_no_results(self, mock_embeddings):
        """Test context retrieval with no results"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()
        rag.vector_store = Mock()
        rag.vector_store.similarity_search_with_score.return_value = []

        context, metadata = rag.get_relevant_context("test query")

        assert context == ""
        assert metadata == []

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_get_relevant_context_formats_correctly(self, mock_embeddings, mock_vector_store):
        """Test that context is properly formatted"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()
        rag.vector_store = mock_vector_store
        rag.hybrid_retriever = None  # Use vector search

        context, metadata = rag.get_relevant_context("test query", max_chunks=2)

        assert context != ""
        assert "[Source" in context
        assert len(metadata) == 2

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_get_relevant_context_uses_hybrid_when_available(self, mock_embeddings, mock_vector_store):
        """Test that hybrid search is preferred when available"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()
        rag.vector_store = mock_vector_store

        # Mock hybrid retriever
        mock_hybrid = Mock()
        mock_hybrid.bm25 = Mock()
        mock_hybrid.retrieve_with_hybrid_and_rerank.return_value = [
            ("Hybrid result", 0.95, {"doc_id": 0, "page": 1, "source": "test.pdf", "section": "Intro"})
        ]
        rag.hybrid_retriever = mock_hybrid

        context, metadata = rag.get_relevant_context("test query", max_chunks=1)

        # Should use hybrid search
        assert "Hybrid result" in context
        mock_hybrid.retrieve_with_hybrid_and_rerank.assert_called_once()


class TestVectorStoreManagement:
    """Test vector store save/load"""

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_save_vector_store_without_store(self, mock_embeddings, temp_dir):
        """Test saving fails without vector store"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()

        with pytest.raises(Exception):  # Should raise VectorStoreError
            rag.save_vector_store(temp_dir)

    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_save_vector_store_success(self, mock_embeddings, mock_faiss, temp_dir, sample_pdf_data):
        """Test successful vector store save"""
        mock_embeddings.return_value = Mock()
        mock_vector_store = Mock()
        mock_faiss.from_documents.return_value = mock_vector_store

        rag = RAGSystem()
        rag.hybrid_retriever = Mock()
        rag.hybrid_retriever.build_bm25_index = Mock()
        rag.process_documents([sample_pdf_data])

        save_path = temp_dir / "vector_store"
        rag.save_vector_store(save_path)

        assert save_path.exists()
        mock_vector_store.save_local.assert_called_once()

    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_load_vector_store_success(self, mock_embeddings, mock_faiss, temp_dir):
        """Test successful vector store load"""
        mock_embeddings.return_value = Mock()
        mock_vector_store = Mock()
        mock_faiss.load_local.return_value = mock_vector_store

        # Create fake saved store
        save_path = temp_dir / "vector_store"
        save_path.mkdir(parents=True)
        (save_path / "faiss_index").mkdir()

        # Create metadata files
        import json
        with open(save_path / "chunks_metadata.json", "w") as f:
            json.dump([{"test": "data"}], f)
        with open(save_path / "documents.json", "w") as f:
            json.dump([{"doc": "data"}], f)

        rag = RAGSystem()
        rag.load_vector_store(save_path)

        assert rag.vector_store is not None
        assert len(rag.chunks_metadata) == 1
        assert len(rag.documents) == 1


class TestMetadataQueries:
    """Test metadata-based queries"""

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_get_chunks_by_document(self, mock_embeddings):
        """Test retrieving chunks by document ID"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()
        rag.chunks_metadata = [
            {"doc_id": 0, "page": 1, "text": "chunk1"},
            {"doc_id": 0, "page": 2, "text": "chunk2"},
            {"doc_id": 1, "page": 1, "text": "chunk3"}
        ]

        chunks = rag.get_chunks_by_document(0)

        assert len(chunks) == 2
        assert all(c['doc_id'] == 0 for c in chunks)

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_get_chunks_by_page(self, mock_embeddings):
        """Test retrieving chunks by page"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()
        rag.chunks_metadata = [
            {"doc_id": 0, "page": 1, "text": "chunk1"},
            {"doc_id": 0, "page": 2, "text": "chunk2"},
            {"doc_id": 1, "page": 1, "text": "chunk3"}
        ]

        chunks = rag.get_chunks_by_page(0, 1)

        assert len(chunks) == 1
        assert chunks[0]['doc_id'] == 0
        assert chunks[0]['page'] == 1


class TestStatistics:
    """Test RAG system statistics"""

    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_get_statistics_empty(self, mock_embeddings):
        """Test statistics for empty system"""
        mock_embeddings.return_value = Mock()

        rag = RAGSystem()
        stats = rag.get_statistics()

        assert stats['total_documents'] == 0
        assert stats['total_chunks'] == 0
        assert stats['has_vector_store'] is False

    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_get_statistics_after_processing(self, mock_embeddings, mock_faiss, sample_pdf_data):
        """Test statistics after document processing"""
        mock_embeddings.return_value = Mock()
        mock_faiss.from_documents.return_value = Mock()

        rag = RAGSystem()
        rag.hybrid_retriever = Mock()
        rag.hybrid_retriever.build_bm25_index = Mock()
        rag.process_documents([sample_pdf_data])

        stats = rag.get_statistics()

        assert stats['total_documents'] == 1
        assert stats['total_chunks'] > 0
        assert stats['has_vector_store'] is True
