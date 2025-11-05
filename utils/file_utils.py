"""
File handling utilities
Provides functions for file validation, sanitization, and management
"""

import re
import hashlib
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from config.settings import (
    ALLOWED_FILE_EXTENSIONS,
    MAX_UPLOAD_SIZE_BYTES,
    SANITIZE_FILENAMES,
    UPLOAD_DIR,
    TEMP_DIR
)
from utils.exceptions import FileSizeError, FileFormatError
from utils.logger import get_logger

logger = get_logger(__name__)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent security issues

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    if not SANITIZE_FILENAMES:
        return filename

    # Remove path components
    filename = Path(filename).name

    # Remove or replace dangerous characters
    filename = re.sub(r'[^\w\s\-\.]', '_', filename)

    # Remove multiple dots (except the last one for extension)
    parts = filename.rsplit('.', 1)
    if len(parts) == 2:
        name, ext = parts
        name = name.replace('.', '_')
        filename = f"{name}.{ext}"

    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1)
        name = name[:250 - len(ext)]
        filename = f"{name}.{ext}"

    return filename


def validate_file(file_path: Path, check_size: bool = True) -> bool:
    """
    Validate file format and size

    Args:
        file_path: Path to file
        check_size: Whether to check file size

    Returns:
        True if valid

    Raises:
        FileFormatError: If file format is invalid
        FileSizeError: If file size exceeds limit
    """
    # Check if file exists
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Check file extension
    if file_path.suffix.lower() not in ALLOWED_FILE_EXTENSIONS:
        raise FileFormatError(
            f"Invalid file format: {file_path.suffix}. "
            f"Allowed formats: {', '.join(ALLOWED_FILE_EXTENSIONS)}"
        )

    # Check file size
    if check_size:
        file_size = file_path.stat().st_size
        if file_size > MAX_UPLOAD_SIZE_BYTES:
            size_mb = file_size / (1024 * 1024)
            max_mb = MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
            raise FileSizeError(
                f"File size ({size_mb:.2f} MB) exceeds maximum "
                f"allowed size ({max_mb:.2f} MB)"
            )

    logger.info(f"File validation passed: {file_path.name}")
    return True


def get_file_hash(file_path: Path) -> str:
    """
    Calculate SHA256 hash of file

    Args:
        file_path: Path to file

    Returns:
        Hex digest of file hash
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def create_unique_filename(original_name: str, base_dir: Path) -> Path:
    """
    Create unique filename to avoid conflicts

    Args:
        original_name: Original filename
        base_dir: Directory where file will be saved

    Returns:
        Unique file path
    """
    sanitized = sanitize_filename(original_name)
    file_path = base_dir / sanitized

    # If file exists, add timestamp
    if file_path.exists():
        stem = file_path.stem
        suffix = file_path.suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{stem}_{timestamp}{suffix}"
        file_path = base_dir / new_name

    return file_path


def save_uploaded_file(uploaded_file, destination_dir: Path = UPLOAD_DIR) -> Path:
    """
    Save uploaded file to disk

    Args:
        uploaded_file: Streamlit UploadedFile object
        destination_dir: Directory to save file

    Returns:
        Path to saved file

    Raises:
        FileSizeError: If file is too large
        FileFormatError: If file format is invalid
    """
    # Check file size
    if uploaded_file.size > MAX_UPLOAD_SIZE_BYTES:
        size_mb = uploaded_file.size / (1024 * 1024)
        max_mb = MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
        raise FileSizeError(
            f"File '{uploaded_file.name}' ({size_mb:.2f} MB) exceeds "
            f"maximum size ({max_mb:.2f} MB)"
        )

    # Create unique filename
    file_path = create_unique_filename(uploaded_file.name, destination_dir)

    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Validate saved file
        validate_file(file_path, check_size=False)

        logger.info(f"File saved: {file_path.name} ({uploaded_file.size / 1024:.2f} KB)")
        return file_path

    except Exception as e:
        # Clean up if save failed
        if file_path.exists():
            file_path.unlink()
        raise


def cleanup_temp_files(directory: Path = TEMP_DIR, max_age_hours: int = 24):
    """
    Clean up old temporary files

    Args:
        directory: Directory to clean
        max_age_hours: Maximum age of files to keep
    """
    try:
        current_time = datetime.now().timestamp()
        max_age_seconds = max_age_hours * 3600

        for file_path in directory.iterdir():
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    logger.info(f"Cleaned up old temp file: {file_path.name}")

    except Exception as e:
        logger.error(f"Error cleaning temp files: {str(e)}")


def get_file_info(file_path: Path) -> dict:
    """
    Get information about a file

    Args:
        file_path: Path to file

    Returns:
        Dictionary with file information
    """
    stat = file_path.stat()
    return {
        "name": file_path.name,
        "size_bytes": stat.st_size,
        "size_mb": stat.st_size / (1024 * 1024),
        "modified": datetime.fromtimestamp(stat.st_mtime),
        "extension": file_path.suffix,
        "hash": get_file_hash(file_path)
    }
