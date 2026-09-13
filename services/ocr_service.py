"""
OCR Service
-----------
Responsible for turning a raw receipt image into plain text.

Pipeline:
    Original Image -> Resize -> Grayscale -> Noise Reduction -> Thresholding -> Tesseract
"""

import cv2
import numpy as np
import pytesseract
import os
import shutil
from flask import current_app


class OCRError(Exception):
    """Raised when OCR processing fails in a way the caller should handle gracefully."""
    pass


def preprocess_image(image_path: str) -> np.ndarray:
    """Load and clean up a receipt image so Tesseract can read it more reliably."""
    image = cv2.imread(image_path)
    if image is None:
        raise OCRError("Could not read the uploaded image. It may be corrupted or an unsupported format.")

    # Resize: upscale small images, cap very large ones (helps OCR accuracy + speed)
    height, width = image.shape[:2]
    target_width = 1200
    if width != target_width:
        scale = target_width / width
        image = cv2.resize(image, (target_width, int(height * scale)), interpolation=cv2.INTER_CUBIC)

    # Grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Noise reduction
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # Thresholding (Otsu's binarization works well for receipts)
    _, thresholded = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return thresholded


def extract_text(image_path: str) -> str:
    """Run the full preprocessing + OCR pipeline and return the raw extracted text."""
    processed = preprocess_image(image_path)
    configured_command = current_app.config.get("TESSERACT_CMD")
    if configured_command and (os.path.isfile(configured_command) or shutil.which(configured_command)):
        pytesseract.pytesseract.tesseract_cmd = configured_command
    else:
        pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract") or "tesseract"

    try:
        text = pytesseract.image_to_string(processed)
    except pytesseract.TesseractNotFoundError as error:
        raise OCRError(
            "Tesseract OCR is not installed or is not available on the server PATH."
        ) from error

    if not text or not text.strip():
        raise OCRError("We couldn't read this receipt clearly. Please upload a clearer image or enter the expense manually.")

    return text
