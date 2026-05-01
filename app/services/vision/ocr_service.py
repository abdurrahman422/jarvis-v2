from pathlib import Path
import shutil

try:
    import cv2
except Exception:
    cv2 = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from PIL import Image
except Exception:
    Image = None


def _preprocess_for_ocr(image_path: Path) -> Path:
    if cv2 is None:
        return image_path
    img = cv2.imread(str(image_path))
    if img is None:
        return image_path
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    denoised = cv2.bilateralFilter(gray, 7, 35, 35)
    thresholded = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        9,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    thresholded = cv2.morphologyEx(thresholded, cv2.MORPH_OPEN, kernel)
    out_path = image_path.parent / f"{image_path.stem}_ocr{image_path.suffix}"
    cv2.imwrite(str(out_path), thresholded)
    return out_path


def _resolve_tesseract() -> tuple[bool, str]:
    if pytesseract is None:
        return False, "pytesseract package missing."
    possible_paths = [
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for p in possible_paths:
        if p and Path(p).exists():
            pytesseract.pytesseract.tesseract_cmd = str(p)
            return True, str(p)
    return False, "Tesseract binary not found. Install Tesseract-OCR and add to PATH."


def image_to_text(image_path: str) -> str:
    p = Path(image_path)
    if not p.exists():
        return "Image not found."
    if pytesseract is None or Image is None:
        return "OCR dependencies missing. Install pytesseract and Pillow."
    ok, detail = _resolve_tesseract()
    if not ok:
        return f"OCR unavailable: {detail}"
    try:
        processed = _preprocess_for_ocr(p)
        txt = pytesseract.image_to_string(
            Image.open(processed),
            config="--oem 3 --psm 6",
        )
        return txt.strip() or "No readable text detected."
    except Exception as exc:
        return f"OCR failed: {exc}. Check that Tesseract is installed and accessible ({detail})."
