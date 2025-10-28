"""
Citation Manager
Handles citation tracking and formatting for research analysis
"""

from typing import List, Dict, Optional, Set
from collections import defaultdict
import json

from utils.logger import get_logger
from utils.exceptions import CitationError

logger = get_logger(__name__)


class CitationManager:
    """
    Manages citations and references throughout the analysis
    """

    def __init__(self):
        """Initialize citation manager"""
        self.citations = []
        self.citation_map = {}  # Maps unique citation keys to citation IDs
        self.next_id = 1  # Start from 1, not 0

        logger.info("Citation manager initialized")

    def add_citation(
        self,
        doc_id: int,
        doc_name: str,
        page_num: int,
        section_name: Optional[str] = None,
        quote: Optional[str] = None,
        context: Optional[str] = None
    ) -> int:
        """
        Add a citation to the manager

        Args:
            doc_id: Document ID
            doc_name: Document name
            page_num: Page number
            section_name: Section name
            quote: Optional quoted text
            context: Optional context information

        Returns:
            Citation ID
        """
        try:
            # Create new citation (always create, no deduplication)
            citation = {
                "id": self.next_id,
                "doc_id": doc_id,
                "doc_name": doc_name,
                "page": page_num,
                "page_num": page_num,  # Include both for compatibility
                "section": section_name,
                "section_name": section_name,  # Include both for compatibility
                "quote": quote,
                "context": context
            }

            self.citations.append(citation)

            logger.debug(f"Added citation: {doc_name}, p.{page_num}, §{section_name}")

            citation_id = self.next_id
            self.next_id += 1

            return citation_id

        except Exception as e:
            logger.error(f"Failed to add citation: {str(e)}")
            raise CitationError(f"Failed to add citation: {str(e)}")

    def add_citations_from_metadata(self, metadata_list: List[Dict]) -> List[int]:
        """
        Add multiple citations from metadata list

        Args:
            metadata_list: List of metadata dictionaries from RAG search

        Returns:
            List of citation IDs
        """
        citation_ids = []

        for metadata in metadata_list:
            try:
                citation_id = self.add_citation(
                    doc_id=metadata.get("doc_id", 0),
                    doc_name=metadata.get("doc_name", "Unknown"),
                    page_num=metadata.get("page", 0),
                    section_name=metadata.get("section"),
                    context=metadata.get("source")
                )
                citation_ids.append(citation_id)

            except Exception as e:
                logger.warning(f"Failed to add citation from metadata: {str(e)}")
                continue

        logger.debug(f"Added {len(citation_ids)} citations from metadata")
        return citation_ids

    def get_citation(self, citation_id: int) -> Optional[Dict]:
        """
        Get citation by ID

        Args:
            citation_id: Citation ID

        Returns:
            Citation dictionary or None
        """
        for citation in self.citations:
            if citation.get('id') == citation_id:
                return citation
        return None

    def format_citation(self, citation_ids: List[int], style: str = "inline") -> str:
        """
        Format citations according to style

        Args:
            citation_ids: List of citation IDs
            style: Citation style ("inline", "footnote", "endnote")

        Returns:
            Formatted citation string
        """
        try:
            if not citation_ids:
                return ""

            # Get citations
            citations = [self.get_citation(cid) for cid in citation_ids]
            citations = [c for c in citations if c is not None]

            if not citations:
                return ""

            if style == "inline":
                return self._format_inline(citations)
            elif style == "footnote":
                return self._format_footnote(citations)
            elif style == "endnote":
                return self._format_endnote(citations)
            else:
                raise ValueError(f"Invalid citation style: {style}. Must be 'inline', 'footnote', or 'endnote'.")

        except ValueError:
            # Re-raise ValueError for invalid style
            raise
        except Exception as e:
            logger.error(f"Failed to format citation: {str(e)}")
            return "[Citation Error]"

    def _format_inline(self, citations: List[Dict]) -> str:
        """
        Format citations as inline references

        Args:
            citations: List of citation dictionaries

        Returns:
            Formatted inline citation
        """
        # Group by document
        by_doc = defaultdict(list)
        for cite in citations:
            doc_name = cite["doc_name"]
            by_doc[doc_name].append(cite)

        # Format: [Doc1, pp.5-7, §2.3; Doc2, p.12, §3.1]
        parts = []
        for doc_name, cites in by_doc.items():
            # Get unique pages
            pages = sorted(set(c["page"] for c in cites))

            # Format pages
            if len(pages) == 1:
                page_str = f"p.{pages[0]}"
            elif len(pages) == 2:
                page_str = f"pp.{pages[0]},{pages[1]}"
            else:
                page_str = f"pp.{pages[0]}-{pages[-1]}"

            # Get unique sections
            sections = [c.get("section") for c in cites if c.get("section")]
            section_str = ""
            if sections:
                unique_sections = list(set(sections))
                if len(unique_sections) == 1:
                    section_str = f", §{unique_sections[0]}"
                elif len(unique_sections) > 1:
                    section_str = f", §{unique_sections[0]} et al."

            parts.append(f"{doc_name}, {page_str}{section_str}")

        return "[" + "; ".join(parts) + "]"

    def _format_footnote(self, citations: List[Dict]) -> str:
        """Format as footnote reference"""
        # Format: [1: Doc Name, p.5]
        parts = []
        for c in citations:
            doc_name = c.get('doc_name', 'Unknown')
            page = c.get('page') or c.get('page_num', '?')
            parts.append(f"{c['id']}: {doc_name}, p.{page}")
        return "[" + "; ".join(parts) + "]"

    def _format_endnote(self, citations: List[Dict]) -> str:
        """Format as endnote reference"""
        # Similar to footnote
        return self._format_footnote(citations)

    def generate_bibliography(self, citation_ids: Optional[List[int]] = None) -> List[Dict]:
        """
        Generate bibliography from citations

        Args:
            citation_ids: Optional list of citation IDs to include (default: all)

        Returns:
            List of bibliography entries
        """
        try:
            if citation_ids is None:
                # Use all citations
                citations_to_use = self.citations
            else:
                citations_to_use = [self.get_citation(cid) for cid in citation_ids]
                citations_to_use = [c for c in citations_to_use if c is not None]

            # Group by document
            by_doc = defaultdict(list)
            for cite in citations_to_use:
                doc_id = cite["doc_id"]
                by_doc[doc_id].append(cite)

            # Create bibliography entries
            bibliography = []
            for doc_id, cites in sorted(by_doc.items()):
                # Get document info from first citation
                first_cite = cites[0]

                # Get all pages referenced
                pages = sorted(set(c["page"] for c in cites))

                entry = {
                    "doc_id": doc_id,
                    "doc_name": first_cite["doc_name"],
                    "pages_cited": pages,
                    "citation_count": len(cites)
                }

                bibliography.append(entry)

            logger.debug(f"Generated bibliography with {len(bibliography)} entries")
            return bibliography

        except Exception as e:
            logger.error(f"Failed to generate bibliography: {str(e)}")
            return []

    def get_citation_statistics(self) -> Dict:
        """
        Get statistics about citations

        Returns:
            Dictionary with citation statistics
        """
        stats = {
            "total_citations": len(self.citations),
            "unique_documents": len(set(c["doc_id"] for c in self.citations)),
            "unique_pages": len(set((c["doc_id"], c["page"]) for c in self.citations)),
            "citations_with_quotes": len([c for c in self.citations if c.get("quote")])
        }

        # Most cited document
        doc_counts = defaultdict(int)
        for cite in self.citations:
            doc_counts[cite["doc_name"]] += 1

        if doc_counts:
            most_cited = max(doc_counts.items(), key=lambda x: x[1])
            stats["most_cited_document"] = most_cited[0]
            stats["most_cited_count"] = most_cited[1]

        return stats

    def save_citations(self, file_path: str):
        """
        Save citations to JSON file

        Args:
            file_path: Path to save file
        """
        try:
            from pathlib import Path
            # Create parent directories if they don't exist
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w") as f:
                json.dump({
                    "citations": self.citations,
                    "next_id": self.next_id
                }, f, indent=2)

            logger.info(f"Citations saved to {file_path}")

        except Exception as e:
            logger.error(f"Failed to save citations: {str(e)}")
            raise CitationError(f"Failed to save citations: {str(e)}")

    def load_citations(self, file_path: str):
        """
        Load citations from JSON file

        Args:
            file_path: Path to load file
        """
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            self.citations = data["citations"]
            self.next_id = data["next_id"]

            # Rebuild citation map
            self.citation_map = {}
            for cite in self.citations:
                citation_key = f"{cite['doc_id']}_{cite['page']}_{cite.get('section')}"
                self.citation_map[citation_key] = cite["id"]

            logger.info(f"Citations loaded from {file_path}")

        except FileNotFoundError:
            logger.warning(f"Citation file not found: {file_path}. Starting with empty citations.")
            # Silently continue with empty citations
            return
        except Exception as e:
            logger.error(f"Failed to load citations: {str(e)}")
            raise CitationError(f"Failed to load citations: {str(e)}")

    def clear(self):
        """Clear all citations"""
        self.citations = []
        self.citation_map = {}
        self.next_id = 1
        logger.info("Citations cleared")

    def clear_citations(self):
        """Clear all citations (alias for clear())"""
        self.clear()

    def get_citations_by_document(self, doc_id: int) -> List[Dict]:
        """
        Get all citations for a specific document

        Args:
            doc_id: Document ID

        Returns:
            List of citation dictionaries for the specified document
        """
        return [c for c in self.citations if c.get('doc_id') == doc_id]
