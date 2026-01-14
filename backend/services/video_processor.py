"""
Video processing service for frame extraction
"""
import io
import base64
import tempfile
from typing import Optional, Callable
import cv2
from PIL import Image


def extract_frames_from_url(
    video_url: str,
    fps: float = 1.0,
    max_frames: int = 30,
    frame_size: tuple[int, int] = (224, 224),
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> list[str]:
    """
    Extract frames from a video URL.
    Returns list of base64 data URLs for each frame.
    """
    import requests

    # Download video to temp file
    response = requests.get(video_url, stream=True, timeout=60)
    response.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
        temp_path = f.name

    try:
        return extract_frames_from_file(temp_path, fps, max_frames, frame_size, progress_callback)
    finally:
        import os
        os.unlink(temp_path)


def extract_frames_from_file(
    file_path: str,
    fps: float = 1.0,
    max_frames: int = 30,
    frame_size: tuple[int, int] = (224, 224),
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> list[str]:
    """
    Extract frames from a video file.
    Returns list of base64 data URLs for each frame.
    """
    cap = cv2.VideoCapture(file_path)

    if not cap.isOpened():
        raise ValueError("Could not open video file")

    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / video_fps if video_fps > 0 else 0

    # Calculate frame interval
    frame_interval = int(video_fps / fps) if fps > 0 else 1
    frame_interval = max(1, frame_interval)

    # Calculate expected frames
    expected_frames = min(max_frames, int(duration * fps))

    frames = []
    frame_idx = 0
    extracted = 0

    while cap.isOpened() and extracted < max_frames:
        ret, frame = cap.read()

        if not ret:
            break

        if frame_idx % frame_interval == 0:
            # Resize frame
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            pil_image = pil_image.resize(frame_size, Image.Resampling.LANCZOS)

            # Convert to base64
            buffer = io.BytesIO()
            pil_image.save(buffer, format='JPEG', quality=85)
            b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            data_url = f"data:image/jpeg;base64,{b64}"

            frames.append(data_url)
            extracted += 1

            if progress_callback:
                progress_callback(extracted, expected_frames)

        frame_idx += 1

    cap.release()
    return frames


def extract_frames_from_data_url(
    data_url: str,
    fps: float = 1.0,
    max_frames: int = 30,
    frame_size: tuple[int, int] = (224, 224),
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> list[str]:
    """
    Extract frames from a base64-encoded video data URL.
    """
    # Decode base64
    header, data = data_url.split(',', 1)
    video_bytes = base64.b64decode(data)

    # Write to temp file
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        f.write(video_bytes)
        temp_path = f.name

    try:
        return extract_frames_from_file(temp_path, fps, max_frames, frame_size, progress_callback)
    finally:
        import os
        os.unlink(temp_path)


def extract_frames(
    source: str,
    fps: float = 1.0,
    max_frames: int = 30,
    frame_size: tuple[int, int] = (224, 224),
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> list[str]:
    """
    Extract frames from any video source (URL, file path, or data URL).
    """
    if source.startswith('data:'):
        return extract_frames_from_data_url(source, fps, max_frames, frame_size, progress_callback)
    elif source.startswith('http://') or source.startswith('https://'):
        return extract_frames_from_url(source, fps, max_frames, frame_size, progress_callback)
    else:
        return extract_frames_from_file(source, fps, max_frames, frame_size, progress_callback)
