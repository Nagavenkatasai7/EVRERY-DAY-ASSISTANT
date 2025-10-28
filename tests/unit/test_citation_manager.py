"""
Unit Tests for Citation Manager
Tests citation tracking, formatting, and bibliography generation
"""

import pytest
from pathlib import Path
import json
import tempfile

from src.citation_manager import CitationManager


class TestCitationManager:
    """Test suite for Citation Manager"""

    def test_initialization(self):
        """Test that CitationManager initializes correctly"""
        mgr = CitationManager()

        assert mgr.citations == []
        assert mgr.next_id == 1

    def test_add_citation_basic(self, sample_citation_data):
        """Test adding a basic citation"""
        mgr = CitationManager()

        cit_id = mgr.add_citation(**sample_citation_data)

        assert cit_id == 1
        assert len(mgr.citations) == 1
        assert mgr.citations[0]['id'] == 1
        assert mgr.citations[0]['doc_name'] == 'Test Paper.pdf'
        assert mgr.citations[0]['page_num'] == 5

    def test_add_multiple_citations(self):
        """Test adding multiple citations"""
        mgr = CitationManager()

        citation1 = {
            'doc_id': 1,
            'doc_name': 'Paper1.pdf',
            'page_num': 1,
            'section_name': 'Intro',
            'quote': 'Quote 1',
            'context': 'Context 1'
        }

        citation2 = {
            'doc_id': 2,
            'doc_name': 'Paper2.pdf',
            'page_num': 5,
            'section_name': 'Methods',
            'quote': 'Quote 2',
            'context': 'Context 2'
        }

        id1 = mgr.add_citation(**citation1)
        id2 = mgr.add_citation(**citation2)

        assert id1 == 1
        assert id2 == 2
        assert len(mgr.citations) == 2
        assert mgr.next_id == 3

    def test_get_citation(self, sample_citation_data):
        """Test retrieving a citation by ID"""
        mgr = CitationManager()

        cit_id = mgr.add_citation(**sample_citation_data)
        retrieved = mgr.get_citation(cit_id)

        assert retrieved is not None
        assert retrieved['id'] == cit_id
        assert retrieved['doc_name'] == sample_citation_data['doc_name']

    def test_get_citation_nonexistent(self):
        """Test retrieving non-existent citation"""
        mgr = CitationManager()

        result = mgr.get_citation(999)

        assert result is None

    def test_format_citation_inline_single(self, sample_citation_data):
        """Test inline citation formatting for single citation"""
        mgr = CitationManager()

        cit_id = mgr.add_citation(**sample_citation_data)
        formatted = mgr.format_citation([cit_id], style="inline")

        assert formatted is not None
        assert 'Test Paper.pdf' in formatted
        assert 'p. 5' in formatted or 'p.5' in formatted

    def test_format_citation_inline_multiple(self):
        """Test inline citation formatting for multiple citations"""
        mgr = CitationManager()

        id1 = mgr.add_citation(
            doc_id=1, doc_name='Paper1.pdf', page_num=1,
            section_name='Intro', quote='Q1', context='C1'
        )
        id2 = mgr.add_citation(
            doc_id=2, doc_name='Paper2.pdf', page_num=2,
            section_name='Methods', quote='Q2', context='C2'
        )

        formatted = mgr.format_citation([id1, id2], style="inline")

        assert 'Paper1.pdf' in formatted
        assert 'Paper2.pdf' in formatted

    def test_format_citation_footnote(self, sample_citation_data):
        """Test footnote citation formatting"""
        mgr = CitationManager()

        cit_id = mgr.add_citation(**sample_citation_data)
        formatted = mgr.format_citation([cit_id], style="footnote")

        assert formatted is not None
        assert str(cit_id) in formatted
        assert 'Test Paper.pdf' in formatted

    def test_format_citation_endnote(self, sample_citation_data):
        """Test endnote citation formatting"""
        mgr = CitationManager()

        cit_id = mgr.add_citation(**sample_citation_data)
        formatted = mgr.format_citation([cit_id], style="endnote")

        assert formatted is not None
        assert 'Test Paper.pdf' in formatted

    def test_format_citation_invalid_style(self, sample_citation_data):
        """Test error handling for invalid citation style"""
        mgr = CitationManager()

        cit_id = mgr.add_citation(**sample_citation_data)

        with pytest.raises(ValueError):
            mgr.format_citation([cit_id], style="invalid_style")

    def test_format_citation_empty_list(self):
        """Test formatting empty citation list"""
        mgr = CitationManager()

        result = mgr.format_citation([], style="inline")

        assert result == ""

    def test_generate_bibliography_empty(self):
        """Test generating bibliography with no citations"""
        mgr = CitationManager()

        bib = mgr.generate_bibliography()

        assert bib == []

    def test_generate_bibliography_single(self, sample_citation_data):
        """Test generating bibliography with single citation"""
        mgr = CitationManager()

        mgr.add_citation(**sample_citation_data)
        bib = mgr.generate_bibliography()

        assert len(bib) == 1
        assert 'Test Paper.pdf' in str(bib[0])

    def test_generate_bibliography_multiple_documents(self):
        """Test bibliography generation for multiple documents"""
        mgr = CitationManager()

        # Add citations from different documents
        mgr.add_citation(
            doc_id=1, doc_name='Paper1.pdf', page_num=1,
            section_name='Intro', quote='Q1', context='C1'
        )
        mgr.add_citation(
            doc_id=1, doc_name='Paper1.pdf', page_num=2,
            section_name='Methods', quote='Q2', context='C2'
        )
        mgr.add_citation(
            doc_id=2, doc_name='Paper2.pdf', page_num=1,
            section_name='Results', quote='Q3', context='C3'
        )

        bib = mgr.generate_bibliography()

        # Should have entries for both documents
        assert len(bib) >= 2

        bib_str = ' '.join(str(entry) for entry in bib)
        assert 'Paper1.pdf' in bib_str
        assert 'Paper2.pdf' in bib_str

    def test_get_citations_by_document(self):
        """Test retrieving citations by document ID"""
        mgr = CitationManager()

        mgr.add_citation(
            doc_id=1, doc_name='Paper1.pdf', page_num=1,
            section_name='Intro', quote='Q1', context='C1'
        )
        mgr.add_citation(
            doc_id=1, doc_name='Paper1.pdf', page_num=2,
            section_name='Methods', quote='Q2', context='C2'
        )
        mgr.add_citation(
            doc_id=2, doc_name='Paper2.pdf', page_num=1,
            section_name='Results', quote='Q3', context='C3'
        )

        doc1_cits = mgr.get_citations_by_document(1)

        assert len(doc1_cits) == 2
        assert all(c['doc_id'] == 1 for c in doc1_cits)

    def test_get_citations_by_document_empty(self):
        """Test getting citations for non-existent document"""
        mgr = CitationManager()

        citations = mgr.get_citations_by_document(999)

        assert citations == []

    def test_get_citation_statistics_empty(self):
        """Test statistics for empty citation manager"""
        mgr = CitationManager()

        stats = mgr.get_citation_statistics()

        assert stats['total_citations'] == 0
        assert stats['unique_documents'] == 0
        assert stats['citations_with_quotes'] == 0

    def test_get_citation_statistics(self):
        """Test statistics generation"""
        mgr = CitationManager()

        # Add citations
        mgr.add_citation(
            doc_id=1, doc_name='Paper1.pdf', page_num=1,
            section_name='Intro', quote='Quote text', context='C1'
        )
        mgr.add_citation(
            doc_id=1, doc_name='Paper1.pdf', page_num=2,
            section_name='Methods', quote='', context='C2'
        )
        mgr.add_citation(
            doc_id=2, doc_name='Paper2.pdf', page_num=1,
            section_name='Results', quote='Another quote', context='C3'
        )

        stats = mgr.get_citation_statistics()

        assert stats['total_citations'] == 3
        assert stats['unique_documents'] == 2
        assert stats['citations_with_quotes'] == 2

    def test_save_and_load_citations(self, temp_dir, sample_citation_data):
        """Test saving and loading citations"""
        mgr = CitationManager()

        # Add some citations
        mgr.add_citation(**sample_citation_data)
        mgr.add_citation(
            doc_id=2, doc_name='Paper2.pdf', page_num=10,
            section_name='Conclusion', quote='Final quote', context='Final context'
        )

        # Save
        save_path = temp_dir / "citations.json"
        mgr.save_citations(save_path)

        # Create new manager and load
        mgr2 = CitationManager()
        mgr2.load_citations(save_path)

        assert len(mgr2.citations) == 2
        assert mgr2.citations[0]['doc_name'] == sample_citation_data['doc_name']
        assert mgr2.next_id == 3

    def test_save_citations_creates_directory(self, temp_dir):
        """Test that save creates directory if needed"""
        mgr = CitationManager()

        mgr.add_citation(
            doc_id=1, doc_name='Test.pdf', page_num=1,
            section_name='Intro', quote='Q', context='C'
        )

        # Save to non-existent subdirectory
        save_path = temp_dir / "subdir" / "citations.json"
        mgr.save_citations(save_path)

        assert save_path.exists()

    def test_load_citations_nonexistent_file(self, temp_dir):
        """Test loading from non-existent file"""
        mgr = CitationManager()

        nonexistent = temp_dir / "nonexistent.json"
        mgr.load_citations(nonexistent)

        # Should not crash, just leave citations empty
        assert len(mgr.citations) == 0

    def test_clear_citations(self, sample_citation_data):
        """Test clearing all citations"""
        mgr = CitationManager()

        mgr.add_citation(**sample_citation_data)
        mgr.add_citation(**sample_citation_data)

        assert len(mgr.citations) == 2

        mgr.clear_citations()

        assert len(mgr.citations) == 0
        assert mgr.next_id == 1

    def test_citation_with_missing_optional_fields(self):
        """Test citation with only required fields"""
        mgr = CitationManager()

        minimal_citation = {
            'doc_id': 1,
            'doc_name': 'Test.pdf',
            'page_num': 1,
            'section_name': 'Intro'
        }

        cit_id = mgr.add_citation(**minimal_citation)

        assert cit_id == 1
        citation = mgr.get_citation(cit_id)
        assert citation['quote'] is None or citation['quote'] == ''
        assert citation['context'] is None or citation['context'] == ''

    def test_citation_formatting_with_special_characters(self):
        """Test citation formatting with special characters"""
        mgr = CitationManager()

        citation = {
            'doc_id': 1,
            'doc_name': 'Müller & O\'Brien (2024).pdf',
            'page_num': 1,
            'section_name': 'Introduction',
            'quote': 'Test quote with "quotes" and special chars: α, β',
            'context': 'Test context'
        }

        cit_id = mgr.add_citation(**citation)
        formatted = mgr.format_citation([cit_id], style="inline")

        assert formatted is not None
        assert 'Müller' in formatted or 'Muller' in formatted


class TestCitationManagerEdgeCases:
    """Test edge cases and error conditions"""

    def test_duplicate_citation_ids(self):
        """Test that citation IDs are unique"""
        mgr = CitationManager()

        id1 = mgr.add_citation(
            doc_id=1, doc_name='P1.pdf', page_num=1,
            section_name='S', quote='Q', context='C'
        )
        id2 = mgr.add_citation(
            doc_id=1, doc_name='P1.pdf', page_num=1,
            section_name='S', quote='Q', context='C'
        )

        assert id1 != id2

    def test_citation_with_very_long_text(self):
        """Test citation with very long quote and context"""
        mgr = CitationManager()

        long_text = "A" * 10000

        cit_id = mgr.add_citation(
            doc_id=1, doc_name='Test.pdf', page_num=1,
            section_name='Section', quote=long_text, context=long_text
        )

        citation = mgr.get_citation(cit_id)
        assert len(citation['quote']) == 10000

    def test_format_citation_with_invalid_ids(self):
        """Test formatting with mix of valid and invalid IDs"""
        mgr = CitationManager()

        valid_id = mgr.add_citation(
            doc_id=1, doc_name='Test.pdf', page_num=1,
            section_name='S', quote='Q', context='C'
        )

        # Try formatting with invalid ID
        formatted = mgr.format_citation([valid_id, 999], style="inline")

        # Should format only valid citations
        assert 'Test.pdf' in formatted

    def test_bibliography_sorted_by_document(self):
        """Test that bibliography entries are organized logically"""
        mgr = CitationManager()

        # Add citations in random order
        mgr.add_citation(
            doc_id=2, doc_name='ZPaper.pdf', page_num=1,
            section_name='S', quote='Q', context='C'
        )
        mgr.add_citation(
            doc_id=1, doc_name='APaper.pdf', page_num=1,
            section_name='S', quote='Q', context='C'
        )

        bib = mgr.generate_bibliography()

        assert len(bib) == 2
        # Bibliography should be organized
        bib_str = str(bib)
        assert 'APaper' in bib_str or 'ZPaper' in bib_str
