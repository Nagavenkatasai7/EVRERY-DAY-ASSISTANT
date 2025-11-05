"""
Document Session Management
Handles storage and retrieval of document analysis sessions
"""

import json
import shutil
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from config.settings import DATA_DIR
from utils.logger import get_logger
from utils.exceptions import RAGSystemError

logger = get_logger(__name__)

# Sessions directory
SESSIONS_DIR = DATA_DIR / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


class DocumentSession:
    """Manages a single document analysis session"""

    def __init__(self, session_id: str, session_name: str = None):
        """Initialize document session"""
        # Validate session_id to prevent path traversal attacks
        if not self._is_valid_session_id(session_id):
            raise ValueError(
                f"Invalid session_id format: {session_id}. "
                f"Expected format: session_YYYYMMDD_HHMMSS"
            )

        self.session_id = session_id
        self.session_name = session_name or f"Session_{session_id}"
        self.session_dir = SESSIONS_DIR / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Session subdirectories
        self.source_pdfs_dir = self.session_dir / "source_pdfs"
        self.summary_dir = self.session_dir / "summary"
        self.rag_dir = self.session_dir / "rag_store"

        self.source_pdfs_dir.mkdir(exist_ok=True)
        self.summary_dir.mkdir(exist_ok=True)
        self.rag_dir.mkdir(exist_ok=True)

        # Metadata
        self.metadata_path = self.session_dir / "metadata.json"
        self.metadata = self._load_metadata()

    @staticmethod
    def _is_valid_session_id(session_id: str) -> bool:
        """
        Validate session_id format to prevent path traversal attacks

        Args:
            session_id: Session ID to validate

        Returns:
            True if valid format, False otherwise
        """
        # Must match format: session_YYYYMMDD_HHMMSS
        pattern = r'^session_\d{8}_\d{6}$'
        return bool(re.match(pattern, session_id))

    def _load_metadata(self) -> Dict:
        """Load session metadata"""
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r') as f:
                return json.load(f)
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "source_pdf_count": 0,
            "has_summary": False,
            "has_rag_store": False,
            "source_pdf_names": [],
            "total_pages": 0,
            "total_images": 0
        }

    def _save_metadata(self):
        """Save session metadata"""
        self.metadata["updated_at"] = datetime.now().isoformat()
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        logger.info(f"Saved metadata for session: {self.session_id}")

    def store_source_pdfs(self, pdf_paths: List[Path]) -> List[Path]:
        """
        Store source PDFs in session

        Args:
            pdf_paths: List of paths to source PDF files

        Returns:
            List of paths to stored PDFs
        """
        try:
            stored_paths = []

            for pdf_path in pdf_paths:
                if not pdf_path.exists():
                    logger.warning(f"PDF not found: {pdf_path}")
                    continue

                # Copy PDF to session directory
                dest_path = self.source_pdfs_dir / pdf_path.name
                shutil.copy2(pdf_path, dest_path)
                stored_paths.append(dest_path)
                logger.info(f"Stored source PDF: {pdf_path.name}")

            # Update metadata
            self.metadata["source_pdf_count"] = len(stored_paths)
            self.metadata["source_pdf_names"] = [p.name for p in stored_paths]
            self._save_metadata()

            return stored_paths

        except Exception as e:
            logger.error(f"Failed to store source PDFs: {str(e)}")
            raise RAGSystemError(f"Failed to store source PDFs: {str(e)}")

    def store_summary_pdf(self, summary_pdf_path: Path) -> Path:
        """
        Store generated summary PDF

        Args:
            summary_pdf_path: Path to generated summary PDF

        Returns:
            Path to stored summary PDF
        """
        try:
            if not summary_pdf_path.exists():
                raise RAGSystemError(f"Summary PDF not found: {summary_pdf_path}")

            # Copy summary PDF
            dest_path = self.summary_dir / summary_pdf_path.name
            shutil.copy2(summary_pdf_path, dest_path)

            # Update metadata
            self.metadata["has_summary"] = True
            self.metadata["summary_pdf_name"] = summary_pdf_path.name
            self._save_metadata()

            logger.info(f"Stored summary PDF: {summary_pdf_path.name}")
            return dest_path

        except Exception as e:
            logger.error(f"Failed to store summary PDF: {str(e)}")
            raise RAGSystemError(f"Failed to store summary PDF: {str(e)}")

    def store_rag_system(self, rag_system):
        """
        Store RAG system vector store

        Args:
            rag_system: RAGSystem instance with vector store
        """
        try:
            rag_system.save_vector_store(self.rag_dir)

            # Update metadata
            self.metadata["has_rag_store"] = True
            self._save_metadata()

            logger.info(f"Stored RAG system for session: {self.session_id}")

        except Exception as e:
            logger.error(f"Failed to store RAG system: {str(e)}")
            raise RAGSystemError(f"Failed to store RAG system: {str(e)}")

    def load_rag_system(self, rag_system):
        """
        Load RAG system vector store

        Args:
            rag_system: RAGSystem instance to load into
        """
        try:
            if not self.metadata["has_rag_store"]:
                raise RAGSystemError("No RAG store found for this session")

            rag_system.load_vector_store(self.rag_dir)
            logger.info(f"Loaded RAG system for session: {self.session_id}")

        except Exception as e:
            logger.error(f"Failed to load RAG system: {str(e)}")
            raise RAGSystemError(f"Failed to load RAG system: {str(e)}")

    def get_source_pdf_paths(self) -> List[Path]:
        """Get paths to all source PDFs"""
        return list(self.source_pdfs_dir.glob("*.pdf"))

    def get_summary_pdf_path(self) -> Optional[Path]:
        """Get path to summary PDF"""
        if self.metadata["has_summary"]:
            summary_name = self.metadata.get("summary_pdf_name", "")
            summary_path = self.summary_dir / summary_name
            if summary_path.exists():
                return summary_path
        return None

    def delete_session(self):
        """Delete entire session directory"""
        try:
            if self.session_dir.exists():
                shutil.rmtree(self.session_dir)
                logger.info(f"Deleted session: {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session: {str(e)}")
            raise RAGSystemError(f"Failed to delete session: {str(e)}")

    def update_statistics(self, total_pages: int, total_images: int):
        """Update session statistics"""
        self.metadata["total_pages"] = total_pages
        self.metadata["total_images"] = total_images
        self._save_metadata()


class SessionManager:
    """Manages all document sessions"""

    @staticmethod
    def list_sessions() -> List[Dict]:
        """
        List all available sessions

        Returns:
            List of session metadata dictionaries
        """
        sessions = []

        for session_dir in SESSIONS_DIR.iterdir():
            if session_dir.is_dir():
                metadata_path = session_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        sessions.append(metadata)

        # Sort by updated_at (most recent first)
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions

    @staticmethod
    def get_session(session_id: str) -> Optional[DocumentSession]:
        """
        Get a specific session

        Args:
            session_id: Session ID

        Returns:
            DocumentSession instance or None
        """
        session_dir = SESSIONS_DIR / session_id
        if session_dir.exists():
            metadata_path = session_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    return DocumentSession(
                        session_id=session_id,
                        session_name=metadata.get("session_name")
                    )
        return None

    @staticmethod
    def create_session(session_name: str = None) -> DocumentSession:
        """
        Create a new session

        Args:
            session_name: Optional custom session name

        Returns:
            New DocumentSession instance
        """
        # Generate unique session ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = f"session_{timestamp}"

        session = DocumentSession(session_id, session_name)
        logger.info(f"Created new session: {session_id}")
        return session

    @staticmethod
    def delete_session(session_id: str):
        """Delete a session"""
        session = SessionManager.get_session(session_id)
        if session:
            session.delete_session()
