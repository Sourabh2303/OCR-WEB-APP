import os
import enum
import logging
from typing import List, Dict, Tuple

import numpy as np
from PIL import Image
import pytesseract

# ------------------------------
# Poppler path for Windows (for pdf2image)
# ------------------------------
POPPLER_PATH = r"C:\Users\DELL\Downloads\Release-25.07.0-0\poppler-25.07.0\Library\bin"

if os.name == "nt" and os.path.isdir(POPPLER_PATH):
    os.environ["PATH"] = POPPLER_PATH + os.pathsep + os.environ.get("PATH", "")
    logging.info(f" Poppler added to PATH: {POPPLER_PATH}")

# ------------------------------
# Imports that depend on Poppler
# ------------------------------
try:
    from pdf2image import convert_from_path
except ImportError:
    raise ImportError("Please install pdf2image: pip install pdf2image")

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

from models import OCRResult  # SQLAlchemy model

logger = logging.getLogger("uvicorn.error")

# ------------------------------
# Auto-detect Tesseract on Windows
# ------------------------------
if os.name == "nt":
    default_tess_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_tess_path):
        pytesseract.pytesseract.tesseract_cmd = default_tess_path
    elif os.getenv("TESSERACT_PATH"):
        pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_PATH")

# ------------------------------
# OCR Engines
# ------------------------------
class SupportedEngine(str, enum.Enum):
    tesseract = "tesseract"
    paddle = "paddle"

_paddle_ocr = None
def get_paddle_ocr():
    """Lazy load PaddleOCR"""
    global _paddle_ocr
    if _paddle_ocr is None:
        if PaddleOCR is None:
            raise RuntimeError("PaddleOCR not installed. Run `pip install paddleocr paddlepaddle`.")
        _paddle_ocr = PaddleOCR(use_angle_cls=True, lang="en")
    return _paddle_ocr

# ------------------------------
# Convert PDF/TIFF to images
# ------------------------------
def _images_from_file(path: str) -> List[Tuple[int, Image.Image]]:
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"File not found: {abs_path}")

    images: List[Tuple[int, Image.Image]] = []
    ext = os.path.splitext(abs_path)[1].lower()

    if ext == ".pdf":
        logger.info(f"📄 Converting PDF to images: {abs_path}")
        pages = convert_from_path(abs_path, poppler_path=POPPLER_PATH)
        if not pages:
            raise RuntimeError("No pages extracted from PDF.")
        for i, page in enumerate(pages, start=1):
            images.append((i, page.convert("RGB")))

    elif ext in {".tif", ".tiff"}:
        logger.info(f" Reading TIFF file: {abs_path}")
        try:
            im = Image.open(abs_path)
            i = 0
            while True:
                im.seek(i)
                images.append((i + 1, im.convert("RGB")))
                i += 1
        except EOFError:
            pass
    else:
        raise ValueError("Unsupported file format. Only PDF and TIFF are supported.")

    logger.info(f"Extracted {len(images)} pages from {abs_path}")
    return images

# ------------------------------
# Tesseract OCR
# ------------------------------
def _ocr_tesseract(image: Image.Image) -> List[Dict]:
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    results = []
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        if text:
            results.append({
                "line_number": i,
                "line_text": text,
                "confidence": float(data["conf"][i]) if data["conf"][i] != "-1" else None,
                "x": int(data["left"][i]),
                "y": int(data["top"][i]),
                "width": int(data["width"][i]),
                "height": int(data["height"][i]),
            })
    return results

# ------------------------------
# PaddleOCR
# ------------------------------
def _ocr_paddle(image: Image.Image) -> List[Dict]:
    ocr = get_paddle_ocr()
    result = ocr.ocr(np.array(image))

    results = []
    if not result or not result[0]:
        return results

    for i, line in enumerate(result[0]):
        try:
            box, (text, confidence) = line
        except Exception as e:
            logger.error(f"PaddleOCR parsing error: {e} | line={line}")
            continue

        if not text:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x, y = int(min(xs)), int(min(ys))
        w, h = int(max(xs) - x), int(max(ys) - y)
        results.append({
            "line_number": i,
            "line_text": text,
            "confidence": float(confidence),
            "x": x,
            "y": y,
            "width": w,
            "height": h,
        })
    return results

# ------------------------------
# Main OCR runner
# ------------------------------
def run_ocr_on_file(path: str, original_name: str, engine: SupportedEngine, db=None) -> Tuple[int, int]:
    images = _images_from_file(path)
    all_results = []

    for page_number, image in images:
        try:
            if engine == SupportedEngine.tesseract:
                rows = _ocr_tesseract(image)
            else:
                rows = _ocr_paddle(image)
        except Exception as e:
            raise RuntimeError(f"OCR failed on page {page_number}: {e}")

        for r in rows:
            r.update({
                "file_name": original_name,
                "page_number": page_number,
            })

        logger.info(f"Page {page_number}: {len(rows)} OCR rows detected.")
        all_results.extend(rows)

    inserted = 0
    if db and all_results:
        try:
            db.bulk_insert_mappings(OCRResult, all_results)
            db.commit()
            inserted = len(all_results)
            logger.info(f" Inserted {inserted} rows into OCRResult table.")
        except Exception as e:
            db.rollback()
            logger.exception(f" DB insert failed: {e}")
            raise

    return inserted, len(images)
