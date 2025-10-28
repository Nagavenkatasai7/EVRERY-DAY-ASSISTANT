"""
PDF Reference Extractor - Extract academic references from PDFs
Automatically identifies DOIs, arXiv IDs, and citation information
"""

from pathlib import Path
from typing import List, Dict, Optional
import re
import fitz  # PyMuPDF

from utils.logger import get_logger

logger = get_logger(__name__)


class PDFReferenceExtractor:
    """
    Extract academic references from PDF documents

    Features:
    - Find References/Bibliography sections
    - Extract DOI and arXiv identifiers
    - Parse author, title, year, journal information
    - Handle various citation formats
    """

    def __init__(self):
        """Initialize reference extractor"""
        # Regex patterns
        self.doi_pattern = re.compile(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE)
        self.arxiv_pattern = re.compile(r'arXiv:\s*(\d{4}\.\d{4,5})', re.IGNORECASE)
        self.year_pattern = re.compile(r'\b((?:19|20)\d{2})\b')
        self.url_pattern = re.compile(r'https?://[^\s]+')

    def extract_references(self, pdf_path: Path) -> List[Dict]:
        """
        Extract all references from a PDF

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of reference dictionaries
        """
        try:
            logger.info(f"📚 Extracting references from: {pdf_path.name}")

            doc = fitz.open(str(pdf_path))

            # Extract document metadata as first reference
            references = []
            doc_ref = self._extract_document_metadata(doc, pdf_path)
            if doc_ref:
                references.append(doc_ref)

            # Find and extract References section
            ref_section_text = self._find_references_section(doc)

            if ref_section_text:
                # Parse individual references
                parsed_refs = self._parse_references(ref_section_text)
                references.extend(parsed_refs)
                logger.info(f"✓ Extracted {len(parsed_refs)} references from {pdf_path.name}")
            else:
                logger.warning(f"No References section found in {pdf_path.name}")

            doc.close()

            return references

        except Exception as e:
            logger.error(f"Failed to extract references from {pdf_path}: {str(e)}")
            return []

    def _extract_document_metadata(self, doc: fitz.Document, pdf_path: Path) -> Optional[Dict]:
        """Extract metadata about the PDF document itself"""
        try:
            metadata = doc.metadata or {}

            # Extract year from metadata or filename
            year = None
            if metadata.get('creationDate'):
                year_match = re.search(r'D:(\d{4})', metadata['creationDate'])
                if year_match:
                    year = int(year_match.group(1))

            # Check filename for year
            if not year:
                filename_year = re.search(r'(19|20)\d{2}', pdf_path.stem)
                if filename_year:
                    year = int(filename_year.group())

            return {
                'type': 'document',
                'authors': metadata.get('author', 'Unknown'),
                'title': metadata.get('title') or pdf_path.stem.replace('_', ' ').replace('-', ' '),
                'year': year,
                'source_file': pdf_path.name,
                'doi': None,
                'arxiv': None,
                'url': None,
                'journal': None,
                'raw_text': f"Source Document: {pdf_path.name}"
            }
        except Exception as e:
            logger.debug(f"Failed to extract document metadata: {str(e)}")
            return None

    def _find_references_section(self, doc: fitz.Document) -> str:
        """
        Find and extract the References/Bibliography section

        Args:
            doc: PyMuPDF document

        Returns:
            Text of references section
        """
        ref_text = ""
        found_refs = False

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()

            # Look for References/Bibliography heading
            if not found_refs:
                # Match various reference section headers
                if re.search(r'\n\s*(References|REFERENCES|Bibliography|BIBLIOGRAPHY|WORKS CITED|References\s+Cited)\s*\n', text):
                    found_refs = True
                    # Extract everything after the heading
                    parts = re.split(
                        r'\n\s*(References|REFERENCES|Bibliography|BIBLIOGRAPHY|WORKS CITED|References\s+Cited)\s*\n',
                        text
                    )
                    if len(parts) > 2:
                        ref_text += parts[-1]
                    continue

            # Continue extracting if we found the section
            if found_refs:
                ref_text += "\n" + text

        return ref_text.strip()

    def _parse_references(self, ref_text: str) -> List[Dict]:
        """
        Parse references text into structured format

        Args:
            ref_text: Raw references text

        Returns:
            List of parsed reference dictionaries
        """
        references = []

        # Split by numbered references or line breaks
        # Common formats: [1], 1., (1), etc.
        ref_entries = re.split(r'\n\s*(?:\[\d+\]|\d+\.|\(\d+\))\s*', ref_text)

        for entry in ref_entries:
            entry = entry.strip()

            # Skip very short entries (likely not real references)
            if len(entry) < 30:
                continue

            # Parse this reference
            ref_dict = self._parse_single_reference(entry)
            if ref_dict:
                references.append(ref_dict)

        return references

    def _parse_single_reference(self, ref_text: str) -> Optional[Dict]:
        """
        Parse a single reference entry

        Args:
            ref_text: Single reference text

        Returns:
            Reference dictionary or None
        """
        try:
            ref = {
                'type': 'reference',
                'raw_text': ref_text,
                'authors': None,
                'title': None,
                'year': None,
                'journal': None,
                'doi': None,
                'arxiv': None,
                'url': None
            }

            # Extract DOI
            doi_match = self.doi_pattern.search(ref_text)
            if doi_match:
                ref['doi'] = doi_match.group()

            # Extract arXiv ID
            arxiv_match = self.arxiv_pattern.search(ref_text)
            if arxiv_match:
                ref['arxiv'] = arxiv_match.group(1)

            # Extract year
            year_matches = self.year_pattern.findall(ref_text)
            if year_matches:
                # Use the first year found (usually publication year)
                ref['year'] = int(year_matches[0])

            # Extract title (usually in quotes or after authors before year)
            # Pattern 1: Text in quotes
            title_match = re.search(r'"([^"]{10,})"', ref_text)
            if title_match:
                ref['title'] = title_match.group(1).strip()
            # Pattern 2: Text ending with period (before year or journal)
            elif not ref['title']:
                # Try to find title between authors and year
                if ref['year']:
                    parts = ref_text.split(str(ref['year']))
                    if parts[0]:
                        # Look for last sentence before year
                        sentences = re.split(r'[.!?]', parts[0])
                        if len(sentences) > 1:
                            ref['title'] = sentences[-1].strip()

            # Extract authors (simplified - text before title or year)
            if ref['year']:
                pre_year = ref_text.split(str(ref['year']))[0]
                # Authors are usually first part with names
                author_part = pre_year.split('.')[0] if '.' in pre_year else pre_year[:100]
                ref['authors'] = author_part.strip().rstrip(',')

            # Extract URL
            url_match = self.url_pattern.search(ref_text)
            if url_match:
                ref['url'] = url_match.group()

            # Extract journal name (text in italics or between title and year)
            # This is harder without markup, so we'll do a basic extraction
            if ref['title'] and ref['year']:
                # Text between title and year might be journal
                title_pos = ref_text.find(ref['title'])
                year_pos = ref_text.find(str(ref['year']))
                if title_pos != -1 and year_pos != -1 and year_pos > title_pos:
                    potential_journal = ref_text[title_pos + len(ref['title']):year_pos]
                    # Clean up
                    potential_journal = re.sub(r'["\',\.]', '', potential_journal).strip()
                    if len(potential_journal) > 3 and len(potential_journal) < 100:
                        ref['journal'] = potential_journal

            # Only return if we extracted something useful
            if ref['doi'] or ref['arxiv'] or ref['title'] or ref['authors']:
                return ref

            return None

        except Exception as e:
            logger.debug(f"Failed to parse reference: {str(e)}")
            return None

    def format_reference_apa(self, ref: Dict) -> str:
        """
        Format reference in APA style

        Args:
            ref: Reference dictionary

        Returns:
            APA formatted string
        """
        parts = []

        # Authors
        if ref.get('authors'):
            parts.append(f"{ref['authors']}.")

        # Year
        if ref.get('year'):
            parts.append(f"({ref['year']}).")

        # Title
        if ref.get('title'):
            parts.append(f"{ref['title']}.")

        # Journal
        if ref.get('journal'):
            parts.append(f"*{ref['journal']}*.")

        # DOI/arXiv/URL
        if ref.get('doi'):
            parts.append(f"https://doi.org/{ref['doi']}")
        elif ref.get('arxiv'):
            parts.append(f"arXiv:{ref['arxiv']}")
        elif ref.get('url'):
            parts.append(ref['url'])

        return " ".join(parts)

    def format_reference_ieee(self, ref: Dict, index: int) -> str:
        """
        Format reference in IEEE style

        Args:
            ref: Reference dictionary
            index: Reference number

        Returns:
            IEEE formatted string
        """
        parts = [f"[{index}]"]

        # Authors
        if ref.get('authors'):
            parts.append(f"{ref['authors']},")

        # Title (in quotes)
        if ref.get('title'):
            parts.append(f'"{ref['title']},"')

        # Journal (italics)
        if ref.get('journal'):
            parts.append(f"*{ref['journal']}*,")

        # Year
        if ref.get('year'):
            parts.append(f"{ref['year']}.")

        # DOI/arXiv/URL
        if ref.get('doi'):
            parts.append(f"DOI: {ref['doi']}")
        elif ref.get('arxiv'):
            parts.append(f"arXiv: {ref['arxiv']}")
        elif ref.get('url'):
            parts.append(f"Available: {ref['url']}")

        return " ".join(parts)

    def get_statistics(self, references: List[Dict]) -> Dict:
        """
        Get statistics about extracted references

        Args:
            references: List of reference dictionaries

        Returns:
            Statistics dictionary
        """
        return {
            'total_references': len(references),
            'with_doi': sum(1 for r in references if r.get('doi')),
            'with_arxiv': sum(1 for r in references if r.get('arxiv')),
            'with_url': sum(1 for r in references if r.get('url')),
            'with_year': sum(1 for r in references if r.get('year')),
            'with_title': sum(1 for r in references if r.get('title')),
        }
