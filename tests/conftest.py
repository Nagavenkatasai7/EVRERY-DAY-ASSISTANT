"""
Pytest Configuration and Fixtures
Provides shared fixtures for all tests
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
import tempfile
import shutil

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def project_root():
    """Return project root directory"""
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def test_data_dir(project_root):
    """Return test data directory"""
    test_dir = project_root / "tests" / "fixtures"
    test_dir.mkdir(parents=True, exist_ok=True)
    return test_dir


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def mock_pdf_document():
    """Mock PyMuPDF document for testing"""
    from unittest.mock import MagicMock

    mock_doc = MagicMock()
    mock_doc.metadata = {
        'author': 'Test Author',
        'title': 'Test Paper',
        'creationDate': 'D:20240101000000'
    }

    # Mock page
    mock_page = MagicMock()
    mock_page.get_text.return_value = """
    Introduction

    This is a test paper about machine learning.

    References

    [1] Smith, J., & Doe, A. (2024). Example Paper Title.
    Journal of Examples, 42(3), 123-456.
    https://doi.org/10.1234/example.2024.123
    arXiv:2024.12345

    [2] Johnson, B. (2023). Another Test Paper.
    Conference Proceedings, 15-30.
    """

    mock_doc.__len__.return_value = 1
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.close = MagicMock()

    return mock_doc


@pytest.fixture
def sample_reference_data():
    """Sample reference data for testing"""
    return {
        'type': 'reference',
        'authors': 'Smith, J., & Doe, A.',
        'title': 'Example Paper Title',
        'year': 2024,
        'journal': 'Journal of Examples',
        'doi': '10.1234/example.2024.123',
        'arxiv': '2024.12345',
        'url': 'https://doi.org/10.1234/example.2024.123',
        'raw_text': 'Smith, J., & Doe, A. (2024). Example Paper Title. Journal of Examples...'
    }


@pytest.fixture
def sample_citation_data():
    """Sample citation data for testing"""
    return {
        'doc_id': 1,
        'doc_name': 'Test Paper.pdf',
        'page_num': 5,
        'section_name': 'Introduction',
        'quote': 'This is a test quote from the paper.',
        'context': 'Testing citation tracking functionality'
    }


@pytest.fixture
def sample_pdf_data():
    """Sample PDF data structure for testing"""
    return {
        "doc_name": "test_document.pdf",
        "pages": [
            {
                "page_num": 1,
                "text": "This is the first page of the test document. It contains important information about machine learning and natural language processing.",
                "section": "Introduction",
                "images": []
            },
            {
                "page_num": 2,
                "text": "This is the second page with more detailed information about neural networks and deep learning architectures.",
                "section": "Methods",
                "images": [
                    {
                        "image_path": "/tmp/test_img.png",
                        "format": "PNG",
                        "page": 2,
                        "index": 0
                    }
                ]
            }
        ]
    }


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(text="This is a test response from Claude.")]
    mock_response.usage = Mock(input_tokens=100, output_tokens=50)
    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_tavily_client():
    """Mock Tavily API client"""
    mock_client = Mock()
    mock_response = {
        'results': [
            {
                'title': 'Test Article 1',
                'url': 'https://example.com/article1',
                'content': 'This is test content from a web search result.',
                'score': 0.95
            },
            {
                'title': 'Test Article 2',
                'url': 'https://example.com/article2',
                'content': 'Another test article with relevant information.',
                'score': 0.88
            }
        ]
    }
    mock_client.search.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_embeddings():
    """Mock HuggingFace embeddings"""
    mock_emb = Mock()
    # Return consistent embedding vectors for testing
    mock_emb.embed_query.return_value = [0.1] * 768
    mock_emb.embed_documents.return_value = [[0.1] * 768, [0.2] * 768, [0.3] * 768]
    return mock_emb


@pytest.fixture
def mock_vector_store():
    """Mock FAISS vector store"""
    from langchain_core.documents import Document

    mock_vs = Mock()

    # Mock similarity search results
    doc1 = Document(
        page_content="Test chunk 1 about machine learning",
        metadata={"doc_id": 0, "doc_name": "test.pdf", "page": 1, "section": "Introduction"}
    )
    doc2 = Document(
        page_content="Test chunk 2 about neural networks",
        metadata={"doc_id": 0, "doc_name": "test.pdf", "page": 2, "section": "Methods"}
    )

    mock_vs.similarity_search_with_score.return_value = [
        (doc1, 0.2),
        (doc2, 0.3)
    ]

    return mock_vs


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests"""
    yield
    # Clean up any global state
    import sys
    modules_to_reload = [
        key for key in sys.modules.keys()
        if key.startswith('src.') or key.startswith('config.')
    ]
    for module in modules_to_reload:
        if hasattr(sys.modules[module], '_instance'):
            sys.modules[module]._instance = None
