import os
import uuid

import cv2
from fastapi import HTTPException, UploadFile, status

from app.config import settings

CHUNK_SIZE = 1024 * 1024  # 1 MB chunk streaming

def validate_extension(filename: str) -> None:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension '{ext}'. Allowed extensions: {settings.ALLOWED_EXTENSIONS}"
        )

async def save_uploaded_video(file: UploadFile) -> tuple[str, str]:
    """
    Streams file upload to disk in 1MB chunks.
    Enforces MAX_UPLOAD_BYTES limit (413 Payload Too Large) and removes partial file.
    Returns (video_path, filename).
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )

    validate_extension(file.filename)

    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1].lower()
    file_name_on_disk = f"{file_id}{ext}"
    video_path = os.path.join(settings.UPLOAD_DIR, file_name_on_disk)

    total_bytes = 0

    try:
        with open(video_path, "wb") as out_file:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > settings.MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed upload size of {settings.MAX_UPLOAD_BYTES} bytes."
                    )
                out_file.write(chunk)
    except Exception as exc:
        if os.path.exists(video_path):
            os.remove(video_path)
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save video: {exc!s}"
        )

    return video_path, file.filename


def probe_video(video_path: str) -> tuple[float, int, int, float]:
    """
    Probes video file using OpenCV.
    Returns (fps, width, height, duration_s).
    Raises HTTPException 400 if video is unreadable or corrupted, and deletes file.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        if os.path.exists(video_path):
            os.remove(video_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded video file is corrupted or unreadable"
        )

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)

    cap.release()

    if fps <= 0 or width <= 0 or height <= 0 or frame_count <= 0:
        if os.path.exists(video_path):
            os.remove(video_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid video metadata: fps, dimensions or frame count are non-positive"
        )

    duration_s = float(frame_count / fps)
    return float(fps), width, height, float(duration_s)
