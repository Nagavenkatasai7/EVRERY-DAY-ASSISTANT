"""
PDF Processing Module
Handles PDF parsing, text extraction, and image extraction
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PIL import Image
import io
import re

from config.settings import TEMP_DIR, IMAGE_DPI
from utils.logger import get_logger
from utils.exceptions import PDFProcessingError, ImageExtractionError
from utils.image_utils import save_image, optimize_image

logger = get_logger(__name__)


class PDFProcessor:
    """Processes PDF documents to extract text and images"""

    def __init__(self, pdf_path: Path):
        """
        Initialize PDF processor

        Args:
            pdf_path: Path to PDF file

        Raises:
            PDFProcessingError: If PDF cannot be opened
        """
        self.pdf_path = pdf_path
        self.doc = None
        self.doc_name = pdf_path.stem

        try:
            self.doc = fitz.open(pdf_path)
            logger.info(f"Opened PDF: {self.doc_name} ({len(self.doc)} pages)")

        except Exception as e:
            logger.error(f"Failed to open PDF {pdf_path}: {str(e)}")
            raise PDFProcessingError(f"Cannot open PDF: {str(e)}")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def close(self):
        """Close PDF document"""
        if self.doc:
            self.doc.close()
            logger.debug(f"Closed PDF: {self.doc_name}")

    def get_metadata(self) -> Dict:
        """
        Extract PDF metadata

        Returns:
            Dictionary with metadata
        """
        try:
            metadata = self.doc.metadata
            return {
                "title": metadata.get("title", "Unknown"),
                "author": metadata.get("author", "Unknown"),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "mod_date": metadata.get("modDate", ""),
                "page_count": len(self.doc),
                "file_size": self.pdf_path.stat().st_size
            }

        except Exception as e:
            logger.warning(f"Failed to extract metadata: {str(e)}")
            return {
                "title": self.doc_name,
                "page_count": len(self.doc) if self.doc else 0
            }

    def extract_text_from_page(self, page_num: int) -> Dict:
        """
        Extract structured text from a page

        Args:
            page_num: Page number (0-indexed)

        Returns:
            Dictionary with text and structure information
        """
        try:
            page = self.doc[page_num]

            # Extract text blocks with position information
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])

            # Extract plain text
            plain_text = page.get_text()

            # Extract text with structure
            structured_text = []
            for block in blocks:
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        line_text = ""
                        for span in line.get("spans", []):
                            line_text += span.get("text", "")
                        if line_text.strip():
                            structured_text.append({
                                "text": line_text,
                                "bbox": line.get("bbox"),
                                "font_size": line.get("spans", [{}])[0].get("size", 0)
                            })

            return {
                "page_num": page_num + 1,  # 1-indexed for user display
                "plain_text": plain_text,
                "structured_text": structured_text,
                "block_count": len(blocks)
            }

        except Exception as e:
            logger.error(f"Failed to extract text from page {page_num + 1}: {str(e)}")
            raise PDFProcessingError(f"Text extraction failed: {str(e)}")

    def extract_images_from_page(self, page_num: int, save_to_disk: bool = True) -> List[Dict]:
        """
        Extract images from a page

        Args:
            page_num: Page number (0-indexed)
            save_to_disk: Whether to save images to disk

        Returns:
            List of dictionaries with image information
        """
        try:
            page = self.doc[page_num]
            image_list = page.get_images()

            extracted_images = []

            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    base_image = self.doc.extract_image(xref)

                    if not base_image:
                        logger.warning(f"Could not extract image {img_index} from page {page_num + 1}")
                        continue

                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    image_width = base_image.get("width", 0)
                    image_height = base_image.get("height", 0)

                    # Convert to PIL Image
                    image = Image.open(io.BytesIO(image_bytes))

                    # Optimize image
                    image = optimize_image(image)

                    # Save to disk if requested
                    image_path = None
                    if save_to_disk:
                        image_filename = f"{self.doc_name}_p{page_num + 1}_img{img_index}.{image_ext}"
                        image_path = TEMP_DIR / image_filename
                        save_image(image, image_path, format=image_ext.upper(), optimize=False)

                    extracted_images.append({
                        "image": image,
                        "image_path": image_path,
                        "format": image_ext,
                        "width": image_width,
                        "height": image_height,
                        "page": page_num + 1,
                        "index": img_index,
                        "xref": xref
                    })

                    logger.debug(f"Extracted image {img_index} from page {page_num + 1}")

                except Exception as e:
                    logger.warning(f"Failed to extract image {img_index} from page {page_num + 1}: {str(e)}")
                    continue

            return extracted_images

        except Exception as e:
            logger.error(f"Failed to extract images from page {page_num + 1}: {str(e)}")
            raise ImageExtractionError(f"Image extraction failed: {str(e)}")

    def detect_section_headers(self, text_data: Dict) -> Optional[str]:
        """
        Detect section headers from text structure

        Args:
            text_data: Text data dictionary from extract_text_from_page

        Returns:
            Section name or None
        """
        try:
            structured_text = text_data.get("structured_text", [])

            # Look for larger font sizes (likely headers)
            if structured_text:
                # Get average font size
                font_sizes = [item["font_size"] for item in structured_text if item.get("font_size", 0) > 0]
                if font_sizes:
                    avg_font_size = sum(font_sizes) / len(font_sizes)

                    # Find text with significantly larger font
                    for item in structured_text:
                        if item.get("font_size", 0) > avg_font_size * 1.2:
                            header_text = item["text"].strip()
                            # Check if it looks like a section header
                            if len(header_text) < 100 and not header_text.endswith('.'):
                                return header_text

            # Fallback: Look for common section patterns in plain text
            plain_text = text_data.get("plain_text", "")
            section_patterns = [
                r'^(\d+\.?\s+[A-Z][^\n]{5,50})\n',
                r'^([A-Z][A-Z\s]{5,50})\n',
                r'^(Introduction|Abstract|Methods|Results|Discussion|Conclusion|References)',
            ]

            for pattern in section_patterns:
                match = re.search(pattern, plain_text, re.MULTILINE | re.IGNORECASE)
                if match:
                    return match.group(1).strip()

            return None

        except Exception as e:
            logger.debug(f"Failed to detect section header: {str(e)}")
            return None

    def process_document(self, extract_images: bool = True) -> Dict:
        """
        Process entire PDF document

        Args:
            extract_images: Whether to extract images

        Returns:
            Dictionary with all extracted data
        """
        try:
            logger.info(f"Processing PDF: {self.doc_name}")

            metadata = self.get_metadata()
            pages_data = []

            for page_num in range(len(self.doc)):
                try:
                    # Extract text
                    text_data = self.extract_text_from_page(page_num)

                    # Detect section
                    section_name = self.detect_section_headers(text_data)

                    # Extract images
                    images = []
                    if extract_images:
                        images = self.extract_images_from_page(page_num, save_to_disk=True)

                    page_data = {
                        "page_num": page_num + 1,
                        "text": text_data["plain_text"],
                        "structured_text": text_data["structured_text"],
                        "section": section_name,
                        "images": images,
                        "image_count": len(images)
                    }

                    pages_data.append(page_data)

                    logger.debug(f"Processed page {page_num + 1}/{len(self.doc)}")

                except Exception as e:
                    logger.error(f"Error processing page {page_num + 1}: {str(e)}")
                    # Continue with other pages
                    pages_data.append({
                        "page_num": page_num + 1,
                        "text": "",
                        "structured_text": [],
                        "section": None,
                        "images": [],
                        "image_count": 0,
                        "error": str(e)
                    })

            result = {
                "doc_name": self.doc_name,
                "doc_path": str(self.pdf_path),
                "metadata": metadata,
                "pages": pages_data,
                "total_pages": len(pages_data),
                "total_images": sum(page["image_count"] for page in pages_data)
            }

            logger.info(f"PDF processing complete: {self.doc_name} "
                       f"({len(pages_data)} pages, {result['total_images']} images)")

            return result

        except Exception as e:
            logger.error(f"Failed to process PDF: {str(e)}")
            raise PDFProcessingError(f"Document processing failed: {str(e)}")


def process_pdf_file(pdf_path: Path, extract_images: bool = True) -> Dict:
    """
    Convenience function to process a PDF file

    Args:
        pdf_path: Path to PDF file
        extract_images: Whether to extract images

    Returns:
        Dictionary with extracted data
    """
    with PDFProcessor(pdf_path) as processor:
        return processor.process_document(extract_images=extract_images)


def process_multiple_pdfs(pdf_paths: List[Path], extract_images: bool = True) -> List[Dict]:
    """
    Process multiple PDF files

    Args:
        pdf_paths: List of PDF file paths
        extract_images: Whether to extract images

    Returns:
        List of dictionaries with extracted data
    """
    results = []

    for pdf_path in pdf_paths:
        try:
            result = process_pdf_file(pdf_path, extract_images=extract_images)
            results.append(result)

        except Exception as e:
            logger.error(f"Failed to process {pdf_path.name}: {str(e)}")
            # Add error entry
            results.append({
                "doc_name": pdf_path.stem,
                "doc_path": str(pdf_path),
                "error": str(e),
                "pages": [],
                "total_pages": 0,
                "total_images": 0
            })

    return results
