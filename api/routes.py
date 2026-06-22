import time
import cv2

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

import shared_state
from config import (
    JPEG_QUALITY,
    VIDEO_STREAM_SLEEP_SECONDS,
    VIDEO_IDLE_SLEEP_SECONDS
)

router = APIRouter()


@router.get("/api/status")
def get_status():
    with shared_state.state_lock:
        return dict(shared_state.current_state)


def mjpeg_generator():
    while True:
        with shared_state.state_lock:
            state = shared_state.current_state.get("state")
            video_enabled = shared_state.current_state.get("video_enabled", True)
            frame = None if shared_state.latest_frame is None else shared_state.latest_frame.copy()

        # ช่วง STARTUP / WAITING / CAPTURED หยุดส่ง feed จริง ๆ
        if not video_enabled or state in ["STARTUP", "WAITING", "CAPTURED"]:
            time.sleep(VIDEO_IDLE_SLEEP_SECONDS)
            continue

        if frame is None:
            time.sleep(VIDEO_IDLE_SLEEP_SECONDS)
            continue

        ok, buffer = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
        )

        if not ok:
            time.sleep(VIDEO_IDLE_SLEEP_SECONDS)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            buffer.tobytes() +
            b"\r\n"
        )

        time.sleep(VIDEO_STREAM_SLEEP_SECONDS)


@router.get("/video_feed")
def video_feed():
    return StreamingResponse(
        mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )