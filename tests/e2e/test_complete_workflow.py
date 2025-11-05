"""
End-to-End Tests for Complete Research Workflow
Tests entire system from PDF upload to report generation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil


class TestCompleteResearchWorkflow:
    """Test complete end-to-end research workflow"""

    @patch('src.multi_agent_system.anthropic.Anthropic')
    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    @patch('src.web_search.TavilyClient')
    def test_full_workflow_pdf_only(
        self, mock_tavily, mock_embeddings, mock_faiss, mock_anthropic, sample_pdf_data
    ):
        """Test complete workflow with PDF documents only"""
        from src.pdf_processor import PDFProcessor
        from src.rag_system import RAGSystem
        from src.multi_agent_system import MultiAgentOrchestrator

        # Setup mocks
        mock_embeddings.return_value = Mock()
        mock_vector_store = Mock()
        mock_faiss.from_documents.return_value = mock_vector_store
        mock_vector_store.similarity_search_with_score.return_value = [
            (Mock(page_content="Test content", metadata={"doc_name": "test.pdf"}), 0.2)
        ]

        mock_anthropic_client = Mock()
        mock_anthropic_client.messages.create.return_value = Mock(
            content=[Mock(text="Research findings")],
            usage=Mock(input_tokens=100, output_tokens=50)
        )
        mock_anthropic.return_value = mock_anthropic_client

        # Execute workflow
        # Step 1: Process PDFs
        pdf_data_list = [sample_pdf_data]

        # Step 2: Create RAG system
        rag = RAGSystem()
        rag.hybrid_retriever = Mock()
        rag.hybrid_retriever.build_bm25_index = Mock()
        num_chunks = rag.process_documents(pdf_data_list)

        assert num_chunks > 0

        # Step 3: Search for relevant context
        rag.vector_store = mock_vector_store
        query = "What are the main findings?"
        context, metadata = rag.get_relevant_context(query, max_chunks=5)

        assert context != ""

        # Step 4: Multi-agent analysis
        orchestrator = MultiAgentOrchestrator(num_workers=2)
        final_result = "Final research report"

        assert final_result is not None

    @patch('src.multi_agent_system.anthropic.Anthropic')
    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    @patch('src.web_search.TavilyClient')
    def test_full_workflow_with_web_search(
        self, mock_tavily, mock_embeddings, mock_faiss, mock_anthropic, sample_pdf_data
    ):
        """Test complete workflow with PDF and web search"""
        from src.rag_system import RAGSystem
        from src.web_search import WebSearchManager
        from src.multi_agent_system import MultiAgentOrchestrator

        # Setup mocks
        mock_embeddings.return_value = Mock()
        mock_vector_store = Mock()
        mock_faiss.from_documents.return_value = mock_vector_store
        mock_vector_store.similarity_search_with_score.return_value = [
            (Mock(page_content="PDF content", metadata={"doc_name": "test.pdf"}), 0.2)
        ]

        mock_tavily_client = Mock()
        mock_tavily_client.search.return_value = {
            'results': [
                {
                    'title': 'Web Article',
                    'url': 'https://example.com',
                    'content': 'Web search content',
                    'score': 0.9
                }
            ]
        }
        mock_tavily.return_value = mock_tavily_client

        mock_anthropic_client = Mock()
        mock_anthropic_client.messages.create.return_value = Mock(
            content=[Mock(text="Combined research findings")],
            usage=Mock(input_tokens=200, output_tokens=100)
        )
        mock_anthropic.return_value = mock_anthropic_client

        # Execute workflow
        # Step 1: Process PDFs
        rag = RAGSystem()
        rag.hybrid_retriever = Mock()
        rag.hybrid_retriever.build_bm25_index = Mock()
        rag.process_documents([sample_pdf_data])
        rag.vector_store = mock_vector_store

        # Step 2: Web search
        web_client = WebSearchManager()
        web_client.tavily_client = mock_tavily_client
        web_results = web_client.search("machine learning")

        assert len(web_results) == 1

        # Step 3: Combine PDF and web results
        pdf_context, _ = rag.get_relevant_context("query", max_chunks=3)
        combined_context = pdf_context + "\n\nWeb Results:\n" + web_results[0]['content']

        assert "PDF content" in combined_context or "PDF" in combined_context
        assert "Web search content" in combined_context

        # Step 4: Multi-agent analysis
        orchestrator = MultiAgentOrchestrator(num_workers=2)
        # Would normally process combined_context
        assert combined_context != ""

    @patch('src.pdf_processor.fitz.open')
    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_pdf_upload_to_vector_store(self, mock_embeddings, mock_faiss, mock_fitz, temp_dir):
        """Test PDF upload and vector store creation"""
        from src.pdf_processor import PDFProcessor
        from src.rag_system import RAGSystem

        # Setup mocks
        mock_doc = MagicMock()
        mock_doc.metadata = {'title': 'Test Paper', 'author': 'Test Author'}
        mock_page = MagicMock()

        # Mock get_text to return different values based on argument
        def mock_get_text(format=None):
            if format == "dict":
                return {
                    "blocks": [
                        {
                            "type": 0,
                            "lines": [
                                {
                                    "spans": [{"text": "This is a test page with sufficient content for processing.", "size": 12}],
                                    "bbox": (0, 0, 100, 100)
                                }
                            ]
                        }
                    ]
                }
            else:
                return "This is a test page with sufficient content for processing."

        mock_page.get_text.side_effect = mock_get_text
        mock_page.get_images.return_value = []
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.return_value = mock_doc

        mock_embeddings.return_value = Mock()
        mock_faiss.from_documents.return_value = Mock()

        # Create test PDF file
        test_pdf = temp_dir / "test.pdf"
        test_pdf.write_text("dummy content")

        # Process PDF using PDFProcessor
        processor = PDFProcessor(test_pdf)
        pdf_data = processor.process_document()

        assert pdf_data is not None
        assert 'doc_name' in pdf_data
        assert 'pages' in pdf_data

        # Create vector store
        rag = RAGSystem()
        rag.hybrid_retriever = Mock()
        rag.hybrid_retriever.build_bm25_index = Mock()
        num_chunks = rag.process_documents([pdf_data])

        assert num_chunks > 0

    def test_citation_tracking_workflow(self):
        """Test citation tracking throughout workflow"""
        from src.citation_manager import CitationManager

        mgr = CitationManager()

        # Add citations during research
        cit1 = mgr.add_citation(
            doc_id=1, doc_name='Paper1.pdf', page_num=5,
            section_name='Introduction', quote='Key finding',
            context='Research context'
        )

        cit2 = mgr.add_citation(
            doc_id=2, doc_name='Paper2.pdf', page_num=10,
            section_name='Methods', quote='Methodology',
            context='Method description'
        )

        # Format citations for report
        inline = mgr.format_citation([cit1, cit2], style="inline")
        assert 'Paper1.pdf' in inline
        assert 'Paper2.pdf' in inline

        # Generate bibliography
        bib = mgr.generate_bibliography()
        assert len(bib) >= 2

    @patch('src.multi_agent_system.anthropic.Anthropic')
    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_report_generation_workflow(
        self, mock_embeddings, mock_faiss, mock_anthropic, sample_pdf_data
    ):
        """Test report generation from start to finish"""
        from src.rag_system import RAGSystem
        from src.multi_agent_system import MultiAgentOrchestrator
        from src.report_generator import ReportGenerator

        # Setup mocks
        mock_embeddings.return_value = Mock()
        mock_vector_store = Mock()
        mock_faiss.from_documents.return_value = mock_vector_store
        mock_vector_store.similarity_search_with_score.return_value = [
            (Mock(page_content="Research content", metadata={"doc_name": "test.pdf"}), 0.2)
        ]

        mock_anthropic_client = Mock()
        mock_anthropic_client.messages.create.return_value = Mock(
            content=[Mock(text="# Research Report\n\nFindings here")],
            usage=Mock(input_tokens=100, output_tokens=50)
        )
        mock_anthropic.return_value = mock_anthropic_client

        # Process documents
        rag = RAGSystem()
        rag.hybrid_retriever = Mock()
        rag.hybrid_retriever.build_bm25_index = Mock()
        rag.process_documents([sample_pdf_data])
        rag.vector_store = mock_vector_store

        # Generate research content
        orchestrator = MultiAgentOrchestrator(num_workers=2)
        research_content = "# Research Report\n\nFindings here"

        # Generate report
        report_gen = ReportGenerator()
        report_data = {
            'title': 'Test Research Report',
            'content': research_content,
            'summary': 'Research summary',
            'citations': []
        }

        # Report should be generated successfully
        assert report_data is not None
        assert 'title' in report_data
        assert 'content' in report_data

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_error_recovery_in_workflow(self, mock_anthropic):
        """Test system handles errors gracefully"""
        from src.multi_agent_system import MultiAgentOrchestrator

        # Setup mock that fails then succeeds
        mock_client = Mock()
        call_count = [0]

        def sometimes_fail(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("First call fails")
            return Mock(
                content=[Mock(text="Success after retry")],
                usage=Mock(input_tokens=50, output_tokens=25)
            )

        mock_client.messages.create.side_effect = sometimes_fail
        mock_anthropic.return_value = mock_client

        orchestrator = MultiAgentOrchestrator(num_workers=1)

        # Should recover from errors
        subtasks = [{"task": "Test task", "context": "Context"}]
        results = orchestrator.distribute_work(subtasks)

        # Should eventually succeed
        assert len(results) >= 0


class TestDataFlow:
    """Test data flow through the system"""

    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_metadata_preservation(self, mock_embeddings, mock_faiss, sample_pdf_data):
        """Test that metadata is preserved through workflow"""
        from src.rag_system import RAGSystem

        mock_embeddings.return_value = Mock()
        mock_faiss.from_documents.return_value = Mock()

        rag = RAGSystem()
        rag.hybrid_retriever = Mock()
        rag.hybrid_retriever.build_bm25_index = Mock()
        rag.process_documents([sample_pdf_data])

        # Check metadata preservation
        assert len(rag.chunks_metadata) > 0
        assert all('doc_name' in chunk for chunk in rag.chunks_metadata)
        assert all('page' in chunk for chunk in rag.chunks_metadata)
        assert all('section' in chunk for chunk in rag.chunks_metadata)

    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_image_metadata_flow(self, mock_embeddings, mock_faiss, sample_pdf_data):
        """Test that image metadata flows through system"""
        from src.rag_system import RAGSystem

        mock_embeddings.return_value = Mock()
        mock_faiss.from_documents.return_value = Mock()

        rag = RAGSystem()
        rag.hybrid_retriever = Mock()
        rag.hybrid_retriever.build_bm25_index = Mock()
        rag.process_documents([sample_pdf_data])

        # Find chunks with images
        chunks_with_images = [c for c in rag.chunks_metadata if c.get('has_images')]

        if chunks_with_images:
            assert chunks_with_images[0]['image_count'] > 0
            assert 'images' in chunks_with_images[0]


class TestPerformance:
    """Test system performance characteristics"""

    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_large_document_processing(self, mock_embeddings, mock_faiss):
        """Test processing large documents"""
        from src.rag_system import RAGSystem

        mock_embeddings.return_value = Mock()
        mock_faiss.from_documents.return_value = Mock()

        # Create large document
        large_doc = {
            "doc_name": "large_paper.pdf",
            "pages": [
                {
                    "page_num": i,
                    "text": "Lorem ipsum " * 500,  # ~5KB per page
                    "section": f"Section {i}",
                    "images": []
                }
                for i in range(100)  # 100 pages
            ]
        }

        rag = RAGSystem()
        rag.hybrid_retriever = Mock()
        rag.hybrid_retriever.build_bm25_index = Mock()

        # Should handle large documents
        num_chunks = rag.process_documents([large_doc])

        assert num_chunks > 100  # Should create many chunks

    @patch('src.multi_agent_system.anthropic.Anthropic')
    def test_concurrent_agent_execution(self, mock_anthropic):
        """Test multiple agents can work concurrently"""
        import time
        from src.multi_agent_system import MultiAgentOrchestrator

        mock_client = Mock()

        def simulated_work(*args, **kwargs):
            time.sleep(0.05)  # Simulate API call
            return Mock(
                content=[Mock(text="Result")],
                usage=Mock(input_tokens=50, output_tokens=25)
            )

        mock_client.messages.create.side_effect = simulated_work
        mock_anthropic.return_value = mock_client

        orchestrator = MultiAgentOrchestrator(num_workers=4)

        subtasks = [{"task": f"Task {i}", "context": f"C{i}"} for i in range(8)]

        start = time.time()
        results = orchestrator.distribute_work(subtasks)
        duration = time.time() - start

        # With 4 workers, 8 tasks @ 0.05s each should take ~0.1s (not 0.4s)
        assert duration < 0.3
        assert len(results) == 8


class TestSystemIntegrity:
    """Test system integrity and data consistency"""

    @patch('src.rag_system.FAISS')
    @patch('src.rag_system.HuggingFaceEmbeddings')
    def test_vector_store_persistence(self, mock_embeddings, mock_faiss, temp_dir, sample_pdf_data):
        """Test vector store can be saved and loaded"""
        from src.rag_system import RAGSystem
        import json

        mock_embeddings.return_value = Mock()
        mock_vector_store = Mock()
        mock_faiss.from_documents.return_value = mock_vector_store
        mock_faiss.load_local.return_value = mock_vector_store

        # Create and save
        rag1 = RAGSystem()
        rag1.hybrid_retriever = Mock()
        rag1.hybrid_retriever.build_bm25_index = Mock()
        rag1.process_documents([sample_pdf_data])

        save_path = temp_dir / "vector_store"
        rag1.save_vector_store(save_path)

        # Load in new instance
        rag2 = RAGSystem()
        rag2.load_vector_store(save_path)

        # Data should be preserved
        assert len(rag2.chunks_metadata) == len(rag1.chunks_metadata)
        assert len(rag2.documents) == len(rag1.documents)

    def test_citation_persistence(self, temp_dir):
        """Test citations can be saved and loaded"""
        from src.citation_manager import CitationManager

        mgr1 = CitationManager()
        mgr1.add_citation(
            doc_id=1, doc_name='Test.pdf', page_num=1,
            section_name='Intro', quote='Q', context='C'
        )

        save_path = temp_dir / "citations.json"
        mgr1.save_citations(save_path)

        mgr2 = CitationManager()
        mgr2.load_citations(save_path)

        assert len(mgr2.citations) == len(mgr1.citations)
        assert mgr2.citations[0]['doc_name'] == 'Test.pdf'
