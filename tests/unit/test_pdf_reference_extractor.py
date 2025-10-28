"""
Unit Tests for PDF Reference Extractor
Tests reference extraction, DOI/arXiv detection, and citation formatting
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import re

from src.pdf_reference_extractor import PDFReferenceExtractor


class TestPDFReferenceExtractor:
    """Test suite for PDF Reference Extractor"""

    def test_initialization(self):
        """Test that extractor initializes with correct patterns"""
        extractor = PDFReferenceExtractor()

        assert extractor.doi_pattern is not None
        assert extractor.arxiv_pattern is not None
        assert extractor.year_pattern is not None
        assert extractor.url_pattern is not None

        # Test DOI pattern
        doi_text = "https://doi.org/10.1234/example.2024.123"
        assert extractor.doi_pattern.search(doi_text) is not None

        # Test arXiv pattern
        arxiv_text = "arXiv:2024.12345"
        assert extractor.arxiv_pattern.search(arxiv_text) is not None

        # Test year pattern
        year_text = "Published in 2024"
        assert extractor.year_pattern.search(year_text) is not None

    def test_doi_pattern_matching(self):
        """Test DOI pattern recognition"""
        extractor = PDFReferenceExtractor()

        valid_dois = [
            "10.1234/example.2024.123",
            "10.1000/xyz123",
            "10.1038/s41586-024-07467-z",
            "10.48550/arXiv.2401.12345"
        ]

        for doi in valid_dois:
            match = extractor.doi_pattern.search(doi)
            assert match is not None, f"Failed to match DOI: {doi}"
            assert match.group() == doi

    def test_arxiv_pattern_matching(self):
        """Test arXiv pattern recognition"""
        extractor = PDFReferenceExtractor()

        valid_arxiv = [
            "arXiv:2024.12345",
            "arXiv: 2301.00001",
            "arxiv:1234.5678"
        ]

        for arxiv in valid_arxiv:
            match = extractor.arxiv_pattern.search(arxiv)
            assert match is not None, f"Failed to match arXiv: {arxiv}"

    def test_parse_single_reference_with_doi(self, sample_reference_data):
        """Test parsing a reference with DOI"""
        extractor = PDFReferenceExtractor()

        ref_text = """
        Smith, J., & Doe, A. (2024). Example Paper Title.
        Journal of Examples, 42(3), 123-456.
        https://doi.org/10.1234/example.2024.123
        """

        result = extractor._parse_single_reference(ref_text)

        assert result is not None
        assert result['doi'] == '10.1234/example.2024.123'
        assert result['year'] == 2024
        assert 'Smith' in result['authors']

    def test_parse_single_reference_with_arxiv(self):
        """Test parsing a reference with arXiv ID"""
        extractor = PDFReferenceExtractor()

        ref_text = """
        Johnson, B. (2023). Deep Learning Paper.
        Conference on Machine Learning.
        arXiv:2023.54321
        """

        result = extractor._parse_single_reference(ref_text)

        assert result is not None
        assert result['arxiv'] == '2023.54321'
        assert result['year'] == 2023

    def test_parse_single_reference_with_title_in_quotes(self):
        """Test parsing reference with title in quotes"""
        extractor = PDFReferenceExtractor()

        ref_text = """
        Brown, C. (2024). "A Comprehensive Study of Natural Language Processing".
        Journal of AI Research, 15(2), 100-120.
        """

        result = extractor._parse_single_reference(ref_text)

        assert result is not None
        assert result['title'] == 'A Comprehensive Study of Natural Language Processing'

    def test_parse_single_reference_short_text(self):
        """Test that very short text is rejected"""
        extractor = PDFReferenceExtractor()

        short_text = "Too short"

        result = extractor._parse_single_reference(short_text)
        assert result is None

    def test_parse_references_multiple_entries(self):
        """Test parsing multiple numbered references"""
        extractor = PDFReferenceExtractor()

        ref_text = """
        [1] Smith, J. (2024). First Paper. Journal A, 10(1), 1-10.
        https://doi.org/10.1234/first.2024

        [2] Johnson, B. (2023). Second Paper. Conference B, 20-30.
        arXiv:2023.00001

        [3] Brown, C. (2022). Third Paper. Journal C, 5(3), 50-60.
        """

        results = extractor._parse_references(ref_text)

        assert len(results) >= 2  # At least 2 valid references
        assert any(r.get('doi') == '10.1234/first.2024' for r in results)
        assert any(r.get('arxiv') == '2023.00001' for r in results)

    def test_format_reference_apa(self, sample_reference_data):
        """Test APA formatting"""
        extractor = PDFReferenceExtractor()

        apa = extractor.format_reference_apa(sample_reference_data)

        assert 'Smith, J., & Doe, A.' in apa
        assert '(2024)' in apa
        assert 'Example Paper Title' in apa
        assert 'https://doi.org/10.1234/example.2024.123' in apa

    def test_format_reference_ieee(self, sample_reference_data):
        """Test IEEE formatting"""
        extractor = PDFReferenceExtractor()

        ieee = extractor.format_reference_ieee(sample_reference_data, 1)

        assert '[1]' in ieee
        assert 'Smith, J., & Doe, A.' in ieee
        assert '2024' in ieee
        assert 'DOI: 10.1234/example.2024.123' in ieee

    def test_format_reference_with_arxiv(self):
        """Test formatting reference with arXiv instead of DOI"""
        extractor = PDFReferenceExtractor()

        ref = {
            'authors': 'Test Author',
            'title': 'Test Title',
            'year': 2024,
            'journal': 'Test Journal',
            'arxiv': '2024.12345',
            'doi': None,
            'url': None
        }

        apa = extractor.format_reference_apa(ref)
        assert 'arXiv:2024.12345' in apa

        ieee = extractor.format_reference_ieee(ref, 1)
        assert 'arXiv: 2024.12345' in ieee

    @patch('fitz.open')
    def test_extract_references_success(self, mock_fitz_open, mock_pdf_document):
        """Test full reference extraction from PDF"""
        mock_fitz_open.return_value = mock_pdf_document

        extractor = PDFReferenceExtractor()
        test_path = Path("/tmp/test.pdf")

        results = extractor.extract_references(test_path)

        assert len(results) > 0
        # Should have at least document metadata
        assert any(r.get('type') == 'document' for r in results)

        mock_fitz_open.assert_called_once()
        mock_pdf_document.close.assert_called_once()

    @patch('fitz.open')
    def test_extract_references_no_references_section(self, mock_fitz_open):
        """Test extraction when no References section exists"""
        mock_doc = MagicMock()
        mock_doc.metadata = {'title': 'Test', 'author': 'Author'}
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Just regular content, no references section."
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page

        mock_fitz_open.return_value = mock_doc

        extractor = PDFReferenceExtractor()
        results = extractor.extract_references(Path("/tmp/test.pdf"))

        # Should still have document metadata
        assert len(results) >= 1
        assert results[0]['type'] == 'document'

    @patch('fitz.open')
    def test_extract_references_error_handling(self, mock_fitz_open):
        """Test error handling in reference extraction"""
        mock_fitz_open.side_effect = Exception("File not found")

        extractor = PDFReferenceExtractor()
        results = extractor.extract_references(Path("/tmp/nonexistent.pdf"))

        # Should return empty list on error
        assert results == []

    def test_find_references_section_various_headings(self):
        """Test finding references with different heading styles"""
        extractor = PDFReferenceExtractor()

        # Test data with different heading styles
        test_cases = [
            "Some text\n\nReferences\n\n[1] First ref",
            "Some text\n\nREFERENCES\n\n[1] First ref",
            "Some text\n\nBibliography\n\n[1] First ref",
            "Some text\n\nWORKS CITED\n\n[1] First ref"
        ]

        for text in test_cases:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = text
            mock_doc.__len__.return_value = 1
            mock_doc.__getitem__.return_value = mock_page

            result = extractor._find_references_section(mock_doc)
            assert "[1] First ref" in result

    def test_extract_document_metadata_from_filename(self):
        """Test extracting year from filename"""
        extractor = PDFReferenceExtractor()

        mock_doc = Mock()
        mock_doc.metadata = {}

        test_path = Path("/tmp/paper_2024_machine_learning.pdf")

        result = extractor._extract_document_metadata(mock_doc, test_path)

        assert result is not None
        assert result['year'] == 2024
        assert 'paper 2024 machine learning' in result['title']

    def test_get_statistics(self, sample_reference_data):
        """Test statistics generation"""
        extractor = PDFReferenceExtractor()

        references = [
            sample_reference_data,
            {
                'type': 'reference',
                'doi': '10.1234/test',
                'arxiv': None,
                'url': None,
                'year': 2023,
                'title': 'Test'
            },
            {
                'type': 'reference',
                'doi': None,
                'arxiv': '2023.12345',
                'url': 'https://arxiv.org/abs/2023.12345',
                'year': None,
                'title': None
            }
        ]

        stats = extractor.get_statistics(references)

        assert stats['total_references'] == 3
        assert stats['with_doi'] == 2
        assert stats['with_arxiv'] == 2
        assert stats['with_url'] == 2
        assert stats['with_year'] == 2
        assert stats['with_title'] == 2


class TestReferencePatternEdgeCases:
    """Test edge cases and malformed references"""

    def test_malformed_doi(self):
        """Test handling of malformed DOI"""
        extractor = PDFReferenceExtractor()

        malformed = [
            "doi: 10",  # Too short
            "10.1234",  # Missing suffix
            "http://notadoi.com/10.1234"  # URL but not DOI URL
        ]

        for text in malformed:
            match = extractor.doi_pattern.search(text)
            # Pattern should be strict and not match malformed DOIs
            if match:
                assert len(match.group()) > 7  # At least 10.xxxx/x

    def test_reference_with_special_characters(self):
        """Test parsing references with special characters"""
        extractor = PDFReferenceExtractor()

        ref_text = """
        Müller, J., & O'Brien, K. (2024). "Machine Learning: A Review".
        AI & ML Journal, 10(2), 100-120.
        https://doi.org/10.1234/ml-review_2024
        """

        result = extractor._parse_single_reference(ref_text)

        assert result is not None
        assert 'Müller' in result['authors']
        assert result['year'] == 2024

    def test_reference_with_multiple_urls(self):
        """Test reference with multiple URLs"""
        extractor = PDFReferenceExtractor()

        ref_text = """
        Smith, J. (2024). Test Paper.
        Available: https://example.com/paper
        DOI: https://doi.org/10.1234/test
        """

        result = extractor._parse_single_reference(ref_text)

        assert result is not None
        # Should extract DOI
        assert result['doi'] == '10.1234/test'
        # Should extract first URL
        assert result['url'] is not None
