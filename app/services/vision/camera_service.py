from pathlib import Path

from app.app_paths import DATA_DIR

try:
    import cv2
except Exception:
    cv2 = None


def capture_single_frame(camera_index: int = 0) -> str:
    if cv2 is None:
        return "OpenCV is not installed. Run: pip install opencv-python"
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        return "Camera is not available."
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return "Could not capture frame."
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / "camera_frame.jpg"
    cv2.imwrite(str(out_path), frame)
    return str(out_path)
