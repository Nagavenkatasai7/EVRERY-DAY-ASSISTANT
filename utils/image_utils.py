"""
Image processing utilities
Handles image extraction, optimization, and conversion
"""

import base64
import io
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image

from config.settings import MAX_IMAGE_SIZE, IMAGE_FORMAT, IMAGE_DPI
from utils.logger import get_logger
from utils.exceptions import ImageExtractionError

logger = get_logger(__name__)


def optimize_image(image: Image.Image, max_size: Tuple[int, int] = MAX_IMAGE_SIZE) -> Image.Image:
    """
    Optimize image size while maintaining aspect ratio

    Args:
        image: PIL Image object
        max_size: Maximum dimensions (width, height)

    Returns:
        Optimized PIL Image
    """
    try:
        # Calculate aspect ratio
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        return image

    except Exception as e:
        logger.error(f"Error optimizing image: {str(e)}")
        raise ImageExtractionError(f"Failed to optimize image: {str(e)}")


def image_to_base64(image: Image.Image, format: str = IMAGE_FORMAT) -> str:
    """
    Convert PIL Image to base64 string

    Args:
        image: PIL Image object
        format: Image format (PNG, JPEG, etc.)

    Returns:
        Base64 encoded string
    """
    try:
        buffered = io.BytesIO()
        image.save(buffered, format=format)
        img_bytes = buffered.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')

    except Exception as e:
        logger.error(f"Error converting image to base64: {str(e)}")
        raise ImageExtractionError(f"Failed to encode image: {str(e)}")


def save_image(image: Image.Image, output_path: Path, format: str = IMAGE_FORMAT, optimize: bool = True) -> Path:
    """
    Save PIL Image to disk

    Args:
        image: PIL Image object
        output_path: Path to save image
        format: Image format
        optimize: Whether to optimize image

    Returns:
        Path to saved image
    """
    try:
        # Optimize if requested
        if optimize:
            image = optimize_image(image)

        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save image
        image.save(output_path, format=format)
        logger.info(f"Image saved: {output_path.name}")
        return output_path

    except Exception as e:
        logger.error(f"Error saving image: {str(e)}")
        raise ImageExtractionError(f"Failed to save image: {str(e)}")


def load_image(file_path: Path) -> Image.Image:
    """
    Load image from file

    Args:
        file_path: Path to image file

    Returns:
        PIL Image object
    """
    try:
        image = Image.open(file_path)
        return image

    except Exception as e:
        logger.error(f"Error loading image from {file_path}: {str(e)}")
        raise ImageExtractionError(f"Failed to load image: {str(e)}")


def get_image_info(image: Image.Image) -> dict:
    """
    Get information about an image

    Args:
        image: PIL Image object

    Returns:
        Dictionary with image information
    """
    return {
        "width": image.width,
        "height": image.height,
        "format": image.format,
        "mode": image.mode,
        "size_bytes": len(image.tobytes())
    }


def create_thumbnail(image: Image.Image, size: Tuple[int, int] = (200, 200)) -> Image.Image:
    """
    Create thumbnail from image

    Args:
        image: PIL Image object
        size: Thumbnail size

    Returns:
        Thumbnail PIL Image
    """
    try:
        thumbnail = image.copy()
        thumbnail.thumbnail(size, Image.Resampling.LANCZOS)
        return thumbnail

    except Exception as e:
        logger.error(f"Error creating thumbnail: {str(e)}")
        raise ImageExtractionError(f"Failed to create thumbnail: {str(e)}")


def convert_image_format(image: Image.Image, target_format: str) -> Image.Image:
    """
    Convert image to different format

    Args:
        image: PIL Image object
        target_format: Target format (PNG, JPEG, etc.)

    Returns:
        Converted PIL Image
    """
    try:
        # Handle RGBA to RGB conversion for JPEG
        if target_format.upper() == "JPEG" and image.mode == "RGBA":
            # Create white background
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])  # Use alpha channel as mask
            return rgb_image

        return image

    except Exception as e:
        logger.error(f"Error converting image format: {str(e)}")
        raise ImageExtractionError(f"Failed to convert image format: {str(e)}")
