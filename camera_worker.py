# camera_worker.py

import time
from datetime import datetime

import cv2

from face_engine import load_face_app, draw_face
from queue_service import save_or_update_queue, get_queue_count
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
    INFER_INTERVAL_SECONDS,
    NO_FACE_TIMEOUT_SECONDS,
    NO_FACE_COOLDOWN_SECONDS,
)
import shared_state


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def update_state(**kwargs):
    with shared_state.state_lock:
        shared_state.current_state.update(kwargs)
        shared_state.current_state["last_update"] = now_text()


def get_runtime_state():
    with shared_state.state_lock:
        return {
            "max_queue": shared_state.max_queue,
            "queue_date_display": shared_state.queue_date_display,
            "disabled_today": shared_state.disabled_today,
            "enable_time": shared_state.enable_time,
            "enable_start_time": shared_state.enable_start_time,
            "enable_end_time": shared_state.enable_end_time,
            "enable_time_display": shared_state.enable_time_display,
            "disabled_reason": shared_state.disabled_reason,
        }


def get_current_disabled_today():
    with shared_state.state_lock:
        return shared_state.disabled_today


def get_current_used_queue():
    with shared_state.state_lock:
        return shared_state.current_state.get("used_queue", 0)


def get_disabled_message():
    with shared_state.state_lock:
        reason = shared_state.disabled_reason

    if reason == "out_of_service_time":
        return "ขณะนี้อยู่นอกเวลารับคิว"

    if reason == "weekend":
        return "งดรับคิววันเสาร์ - อาทิตย์"

    return "งดบริการแจกคิว"


def queue_no_to_int(queue_no):
    try:
        return int(str(queue_no))
    except Exception:
        return 0


def set_latest_frame(frame):
    with shared_state.state_lock:
        shared_state.latest_frame = frame.copy()


def clear_latest_frame():
    with shared_state.state_lock:
        shared_state.latest_frame = None


def set_disabled_state():
    runtime = get_runtime_state()

    update_state(
        state="DISABLED_TODAY",
        message=get_disabled_message(),
        queue_no="",
        det_score=0.0,
        similarity=None,
        can_print=False,
        last_event_id=0,
        wait_remaining=0,
        video_enabled=False,
        used_queue=0,
        **runtime,
    )

    clear_latest_frame()


def close_camera(cap):
    if cap is not None:
        try:
            cap.release()
        except Exception:
            pass


def open_camera():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def camera_loop():
    face_app = None
    cap = None

    next_scan_time = 0
    face_ready_since = None
    no_face_since = None
    last_infer_time = 0
    last_faces = []
    wait_reason = "next_person"

    while True:

        if get_current_disabled_today():
            close_camera(cap)
            cap = None
            face_app = None

            set_disabled_state()
            face_ready_since = None
            no_face_since = None
            last_faces = []

            time.sleep(WAIT_SLEEP_SECONDS)
            continue

        if face_app is None:
            runtime = get_runtime_state()
            initial_used_queue = get_queue_count()

            update_state(
                state="STARTUP",
                message="กำลังเริ่มระบบ กรุณาออกห่างจากกล้อง",
                queue_no="",
                det_score=0.0,
                similarity=None,
                can_print=False,
                last_event_id=0,
                wait_remaining=STARTUP_COOLDOWN_SECONDS,
                video_enabled=False,
                used_queue=initial_used_queue,
                **runtime,
            )

            face_app = load_face_app()

            startup_until = time.time() + STARTUP_COOLDOWN_SECONDS

            while time.time() < startup_until:
                if get_current_disabled_today():
                    break

                remaining = max(0, int(startup_until - time.time()))
                runtime = get_runtime_state()

                update_state(
                    state="STARTUP",
                    message=f"กำลังเริ่มระบบ กรุณารอ {remaining} วินาที",
                    queue_no="",
                    det_score=0.0,
                    similarity=None,
                    can_print=False,
                    last_event_id=0,
                    wait_remaining=remaining,
                    video_enabled=False,
                    used_queue=get_current_used_queue(),
                    **runtime,
                )

                clear_latest_frame()
                time.sleep(WAIT_SLEEP_SECONDS)

            next_scan_time = 0
            face_ready_since = None
            no_face_since = None
            last_infer_time = 0
            last_faces = []

            continue

        if cap is None:
            cap = open_camera()

            if not cap.isOpened():
                runtime = get_runtime_state()

                update_state(
                    state="ERROR",
                    message="เปิดกล้องไม่ได้",
                    queue_no="",
                    det_score=0.0,
                    similarity=None,
                    can_print=False,
                    wait_remaining=0,
                    video_enabled=False,
                    used_queue=get_current_used_queue(),
                    **runtime,
                )

                close_camera(cap)
                cap = None
                time.sleep(1)
                continue

            runtime = get_runtime_state()

            update_state(
                state="READY",
                message="กรุณามองที่กล้อง",
                queue_no="",
                det_score=0.0,
                similarity=None,
                can_print=False,
                last_event_id=0,
                wait_remaining=0,
                video_enabled=True,
                used_queue=get_current_used_queue(),
                **runtime,
            )

        now = time.time()

        if now < next_scan_time:
            remaining = max(0, int(next_scan_time - now))
            runtime = get_runtime_state()

            if wait_reason == "no_face":
                wait_message = (
                    f"ไม่พบใบหน้า พักการสแกน {remaining} วินาที"
                )
            else:
                wait_message = (
                    f"กรุณารอ {remaining} วินาที ก่อนสแกนคนถัดไป"
                )

            update_state(
                state="WAITING",
                message=wait_message,
                queue_no="",
                det_score=0.0,
                similarity=None,
                can_print=False,
                wait_remaining=remaining,
                video_enabled=False,
                used_queue=get_current_used_queue(),
                **runtime,
            )

            face_ready_since = None
            no_face_since = None
            clear_latest_frame()
            time.sleep(WAIT_SLEEP_SECONDS)
            continue

        ret, frame = cap.read()

        if not ret:
            runtime = get_runtime_state()

            update_state(
                state="ERROR",
                message="อ่านภาพจากกล้องไม่ได้",
                queue_no="",
                det_score=0.0,
                similarity=None,
                can_print=False,
                wait_remaining=0,
                video_enabled=False,
                used_queue=get_current_used_queue(),
                **runtime,
            )

            clear_latest_frame()
            close_camera(cap)
            cap = None
            time.sleep(1)
            continue

        if now - last_infer_time >= INFER_INTERVAL_SECONDS:
            faces = face_app.get(frame)
            last_faces = faces
            last_infer_time = now
        else:
            faces = last_faces

        if len(faces) == 1:
            no_face_since = None
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

                runtime = get_runtime_state()

                update_state(
                    state="SCANNING",
                    message=f"พบใบหน้า กรุณานิ่งไว้ {remaining_stable:.1f} วินาที",
                    queue_no="",
                    det_score=det_score,
                    similarity=None,
                    can_print=False,
                    wait_remaining=0,
                    video_enabled=True,
                    used_queue=get_current_used_queue(),
                    **runtime,
                )

                if stable_time >= AUTO_CAPTURE_STABLE_SECONDS:
                    result = save_or_update_queue(
                        embedding=face.embedding,
                        det_score=det_score,
                    )

                    event_id = int(time.time() * 1000)

                    if result.get("status") == "new_face":
                        used_queue = queue_no_to_int(result.get("queue_no"))
                    else:
                        used_queue = get_current_used_queue()

                    runtime = get_runtime_state()

                    if result.get("status") == "queue_full":
                        update_state(
                            state="QUEUE_FULL",
                            message=result.get(
                                "message",
                                "คิวเต็มแล้ว กรุณาติดต่อเจ้าหน้าที่",
                            ),
                            queue_no="",
                            det_score=det_score,
                            similarity=None,
                            can_print=False,
                            last_event_id=event_id,
                            wait_remaining=0,
                            video_enabled=True,
                            used_queue=used_queue,
                            **runtime,
                        )
                    else:
                        update_state(
                            state="CAPTURED",
                            message=result.get("message", "สแกนสำเร็จ"),
                            queue_no=result.get("queue_no", ""),
                            det_score=det_score,
                            similarity=result.get("similarity"),
                            can_print=result.get("can_print", False),
                            last_event_id=event_id,
                            wait_remaining=0,
                            video_enabled=True,
                            used_queue=used_queue,
                            **runtime,
                        )

                    face_ready_since = None
                    time.sleep(RESULT_DISPLAY_SECONDS)

                    clear_latest_frame()
                    wait_reason = "next_person"
                    next_scan_time = time.time() + CAPTURE_COOLDOWN_SECONDS
                    time.sleep(WAIT_SLEEP_SECONDS)

            else:
                face_ready_since = None
                runtime = get_runtime_state()

                update_state(
                    state="SCANNING",
                    message="พบใบหน้า แต่ภาพยังไม่ชัด กรุณาขยับเข้าใกล้กล้อง",
                    queue_no="",
                    det_score=det_score,
                    similarity=None,
                    can_print=False,
                    wait_remaining=0,
                    video_enabled=True,
                    used_queue=get_current_used_queue(),
                    **runtime,
                )

        elif len(faces) > 1:
            face_ready_since = None
            no_face_since = None
            set_latest_frame(frame)
            runtime = get_runtime_state()

            update_state(
                state="MULTI_FACE",
                message="พบมากกว่า 1 ใบหน้า กรุณาให้เหลือ 1 คน",
                queue_no="",
                det_score=0.0,
                similarity=None,
                can_print=False,
                wait_remaining=0,
                video_enabled=True,
                used_queue=get_current_used_queue(),
                **runtime,
            )

        else:
            face_ready_since = None
            set_latest_frame(frame)

            if no_face_since is None:
                no_face_since = now

            no_face_elapsed = now - no_face_since

            if no_face_elapsed >= NO_FACE_TIMEOUT_SECONDS:
                runtime = get_runtime_state()

                wait_reason = "no_face"
                next_scan_time = time.time() + NO_FACE_COOLDOWN_SECONDS
                no_face_since = None

                update_state(
                    state="WAITING",
                    message=(
                        f"ไม่พบใบหน้า พักการสแกน "
                        f"{NO_FACE_COOLDOWN_SECONDS} วินาที"
                    ),
                    queue_no="",
                    det_score=0.0,
                    similarity=None,
                    can_print=False,
                    wait_remaining=NO_FACE_COOLDOWN_SECONDS,
                    video_enabled=False,
                    used_queue=get_current_used_queue(),
                    **runtime,
                )

                clear_latest_frame()
                time.sleep(WAIT_SLEEP_SECONDS)
                continue

            runtime = get_runtime_state()

            update_state(
                state="READY",
                message="กรุณามองที่กล้อง",
                queue_no="",
                det_score=0.0,
                similarity=None,
                can_print=False,
                wait_remaining=0,
                video_enabled=True,
                used_queue=get_current_used_queue(),
                **runtime,
            )

        time.sleep(SCAN_SLEEP_SECONDS)
