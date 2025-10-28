"""
Custom Exceptions for the Research Assistant Application
Provides specific error types for better error handling
"""

class ResearchAssistantError(Exception):
    """Base exception for all application errors"""
    pass


class PDFProcessingError(ResearchAssistantError):
    """Raised when PDF processing fails"""
    pass


class ImageExtractionError(ResearchAssistantError):
    """Raised when image extraction from PDF fails"""
    pass


class APIError(ResearchAssistantError):
    """Raised when API calls fail"""
    pass


class ClaudeAPIError(APIError):
    """Raised when Claude API calls fail"""
    pass


class RateLimitError(APIError):
    """Raised when API rate limits are exceeded"""
    pass


class AuthenticationError(APIError):
    """Raised when API authentication fails"""
    pass


class RAGSystemError(ResearchAssistantError):
    """Raised when RAG system operations fail"""
    pass


class VectorStoreError(RAGSystemError):
    """Raised when vector store operations fail"""
    pass


class EmbeddingError(RAGSystemError):
    """Raised when embedding generation fails"""
    pass


class CitationError(ResearchAssistantError):
    """Raised when citation tracking/generation fails"""
    pass


class ReportGenerationError(ResearchAssistantError):
    """Raised when PDF report generation fails"""
    pass


class ValidationError(ResearchAssistantError):
    """Raised when input validation fails"""
    pass


class FileSizeError(ValidationError):
    """Raised when file size exceeds limits"""
    pass


class FileFormatError(ValidationError):
    """Raised when file format is invalid"""
    pass


class ConfigurationError(ResearchAssistantError):
    """Raised when configuration is invalid"""
    pass


class TimeoutError(ResearchAssistantError):
    """Raised when operations exceed timeout limits"""
    pass
