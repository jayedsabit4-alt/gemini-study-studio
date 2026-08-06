"""OCR Text Extraction Helper Module."""

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


def extract_text_from_image(
    file_bytes: bytes, filename: str = ""
) -> Tuple[str, Dict[str, Any], List[str]]:
    """Extracts text from image bytes using PIL and pytesseract if available."""
    warnings: List[str] = []
    try:
        import io
        from PIL import Image
        import pytesseract

        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image)
        metadata = {"image_size": image.size, "image_mode": image.mode}
        if not text.strip():
            warnings.append("OCR completed but no readable text was detected in image.")
        return text, metadata, warnings
    except Exception as err:
        logger.warning("OCR execution skipped or failed for %s: %s", filename, err)
        warnings.append(f"OCR unavailable or failed: {str(err)}")
        return "", {"image_size": (0, 0)}, warnings
