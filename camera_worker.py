import time
from datetime import datetime

import cv2

from face_engine import load_face_app, draw_face
from queue_service import save_or_update_queue
from config import (
    DET_SCORE_THRESHOLD,
    STARTUP_COOLDOWN_SECONDS,
    CAPTURE_COOLDOWN_SECONDS,
    CAMERA_INDEX,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    SCAN_SLEEP_SECONDS,
    WAIT_SLEEP_SECONDS,
    AUTO_CAPTURE_STABLE_SECONDS,
    RESULT_DISPLAY_SECONDS,
)
import shared_state


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def update_state(**kwargs):
    with shared_state.state_lock:
        shared_state.current_state.update(kwargs)
        shared_state.current_state["last_update"] = now_text()


def set_latest_frame(frame):
    with shared_state.state_lock:
        shared_state.latest_frame = frame.copy()


def clear_latest_frame():
    with shared_state.state_lock:
        shared_state.latest_frame = None


def camera_loop():
    update_state(
        state="STARTUP",
        message="กำลังเริ่มระบบ กรุณาออกห่างจากกล้อง",
        queue_no="",
        det_score=0.0,
        similarity=None,
        can_print=False,
        last_event_id=0,
        wait_remaining=STARTUP_COOLDOWN_SECONDS,
        video_enabled=False
    )

    face_app = load_face_app()

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        update_state(
            state="ERROR",
            message="เปิดกล้องไม่ได้",
            video_enabled=False
        )
        return

    startup_until = time.time() + STARTUP_COOLDOWN_SECONDS

    while time.time() < startup_until:
        remaining = max(0, int(startup_until - time.time()))

        update_state(
            state="STARTUP",
            message=f"กำลังเริ่มระบบ กรุณารอ {remaining} วินาที",
            wait_remaining=remaining,
            video_enabled=False
        )

        clear_latest_frame()
        time.sleep(WAIT_SLEEP_SECONDS)

    update_state(
        state="READY",
        message="กรุณามองที่กล้อง",
        queue_no="",
        det_score=0.0,
        similarity=None,
        can_print=False,
        last_event_id=0,
        wait_remaining=0,
        video_enabled=True
    )

    next_scan_time = 0
    face_ready_since = None

    while True:
        now = time.time()

        if now < next_scan_time:
            remaining = max(0, int(next_scan_time - now))

            update_state(
                state="WAITING",
                message=f"กรุณารอ {remaining} วินาที ก่อนสแกนคนถัดไป",
                det_score=0.0,
                wait_remaining=remaining,
                video_enabled=False
            )

            face_ready_since = None
            clear_latest_frame()
            time.sleep(WAIT_SLEEP_SECONDS)
            continue

        ret, frame = cap.read()

        if not ret:
            update_state(
                state="ERROR",
                message="อ่านภาพจากกล้องไม่ได้",
                video_enabled=False
            )
            clear_latest_frame()
            time.sleep(1)
            continue

        faces = face_app.get(frame)

        if len(faces) == 1:
            face = faces[0]
            det_score = float(face.det_score)

            draw_face(frame, face, f"det_score: {det_score:.3f}")
            set_latest_frame(frame)

            if det_score >= DET_SCORE_THRESHOLD:
                if face_ready_since is None:
                    face_ready_since = time.time()

                stable_time = time.time() - face_ready_since
                remaining_stable = max(
                    0,
                    AUTO_CAPTURE_STABLE_SECONDS - stable_time
                )

                update_state(
                    state="SCANNING",
                    message=f"พบใบหน้า กรุณานิ่งไว้ {remaining_stable:.1f} วินาที",
                    det_score=det_score,
                    wait_remaining=0,
                    video_enabled=True
                )

                if stable_time >= AUTO_CAPTURE_STABLE_SECONDS:
                    result = save_or_update_queue(
                        embedding=face.embedding,
                        det_score=det_score
                    )

                    event_id = int(time.time() * 1000)

                    update_state(
                        state="CAPTURED",
                        message=result.get("message", "สแกนสำเร็จ"),
                        queue_no=result.get("queue_no", ""),
                        similarity=result.get("similarity"),
                        can_print=result.get("can_print", False),
                        last_event_id=event_id,
                        wait_remaining=0,
                        video_enabled=True
                    )

                    face_ready_since = None

                    # ค้างหน้าผลลัพธ์ 3 วินาที เช่น ออกคิวใหม่ / พบใบหน้าเดิม
                    time.sleep(RESULT_DISPLAY_SECONDS)

                    # หลังแสดงผลลัพธ์แล้ว ค่อยปิด video feed เพื่อประหยัด CPU
                    clear_latest_frame()

                    next_scan_time = time.time() + CAPTURE_COOLDOWN_SECONDS
                    time.sleep(WAIT_SLEEP_SECONDS)

            else:
                face_ready_since = None

                update_state(
                    state="SCANNING",
                    message="พบใบหน้า แต่ภาพยังไม่ชัด กรุณาขยับเข้าใกล้กล้อง",
                    det_score=det_score,
                    wait_remaining=0,
                    video_enabled=True
                )

        elif len(faces) > 1:
            face_ready_since = None
            set_latest_frame(frame)

            update_state(
                state="MULTI_FACE",
                message="พบมากกว่า 1 ใบหน้า กรุณาให้เหลือ 1 คน",
                queue_no="",
                det_score=0.0,
                similarity=None,
                wait_remaining=0,
                video_enabled=True
            )

        else:
            face_ready_since = None
            set_latest_frame(frame)

            update_state(
                state="READY",
                message="กรุณามองที่กล้อง",
                queue_no="",
                det_score=0.0,
                similarity=None,
                wait_remaining=0,
                video_enabled=True
            )

        time.sleep(SCAN_SLEEP_SECONDS)