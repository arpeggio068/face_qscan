import time
import cv2

from db import init_db
from face_engine import load_face_app, draw_face
from queue_service import save_or_update_queue
from config import (
    DET_SCORE_THRESHOLD,
    CAPTURE_COOLDOWN_SECONDS,
    STARTUP_COOLDOWN_SECONDS,
    CAMERA_INDEX,
    WINDOW_NAME
)


STATE_STARTUP = "STARTUP"
STATE_READY = "READY"
STATE_WAITING = "WAITING"


def fake_print_ticket(result):
    print("")
    print("========== PRINT TICKET ==========")
    print("QUEUE NO:", result.get("queue_no"))
    print("STATUS:", result.get("status"))
    print("MESSAGE:", result.get("message"))

    if "similarity" in result:
        print("SIMILARITY:", round(result["similarity"], 4))

    print("CAN PRINT:", result.get("can_print"))
    print("==================================")
    print("")


def draw_center_text(frame, text, y, scale=1.2, thickness=3):
    h, w = frame.shape[:2]

    text_size, _ = cv2.getTextSize(
        text,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        thickness
    )

    x = int((w - text_size[0]) / 2)

    cv2.putText(
        frame,
        text,
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (0, 255, 255),
        thickness
    )


def check_exit_key():
    key = cv2.waitKey(1) & 0xFF
    return key == 27 or key in [ord("q"), ord("Q")]


def show_startup_screen(cap):
    wait_until = time.time() + STARTUP_COOLDOWN_SECONDS

    while True:
        now = time.time()
        remaining = int(wait_until - now)

        if remaining <= 0:
            return True

        ret, frame = cap.read()

        if not ret:
            time.sleep(0.2)
            continue

        draw_center_text(
            frame,
            "SYSTEM STARTING",
            160,
            scale=1.4,
            thickness=4
        )

        draw_center_text(
            frame,
            f"Scan enabled in {remaining} sec",
            230,
            scale=1.1,
            thickness=3
        )

        draw_center_text(
            frame,
            "Please step away from camera",
            300,
            scale=0.8,
            thickness=2
        )

        draw_center_text(
            frame,
            "Press ESC to exit",
            360,
            scale=0.8,
            thickness=2
        )

        cv2.imshow(WINDOW_NAME, frame)

        if check_exit_key():
            return False

        time.sleep(0.2)


def show_waiting_screen(cap, wait_until):
    """
    ช่วง WAITING:
    - ไม่เรียก face_app.get()
    - ไม่ detect face
    - อ่านกล้องแค่เบา ๆ เพื่อให้หน้าจอยังไม่ค้าง
    - sleep ทีละ 0.2 วินาทีเพื่อลด CPU
    """

    while True:
        now = time.time()
        remaining = int(wait_until - now)

        if remaining <= 0:
            return True

        ret, frame = cap.read()

        if not ret:
            time.sleep(0.2)
            continue

        draw_center_text(
            frame,
            "PLEASE WAIT",
            180,
            scale=1.5,
            thickness=4
        )

        draw_center_text(
            frame,
            f"Ready in {remaining} sec",
            250,
            scale=1.2,
            thickness=3
        )

        draw_center_text(
            frame,
            "Press ESC to exit",
            330,
            scale=0.8,
            thickness=2
        )

        cv2.imshow(WINDOW_NAME, frame)

        if check_exit_key():
            return False

        time.sleep(0.2)


def main():
    init_db()

    face_app = load_face_app()

    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("เปิดกล้องไม่ได้")
        return

    print("ระบบพร้อมทำงาน")
    print(f"เริ่มระบบจะพัก {STARTUP_COOLDOWN_SECONDS} วินาที ก่อนเปิดสแกน")
    print(f"Auto capture เมื่อ det_score >= {DET_SCORE_THRESHOLD}")
    print(f"หลัง capture จะพักระบบ {CAPTURE_COOLDOWN_SECONDS} วินาที")
    print("กด ESC หรือ Q เพื่อออก")

    state = STATE_STARTUP

    try:
        while True:
            if state == STATE_STARTUP:
                ok = show_startup_screen(cap)

                if not ok:
                    break

                state = STATE_READY
                continue

            if state == STATE_WAITING:
                wait_until = time.time() + CAPTURE_COOLDOWN_SECONDS

                ok = show_waiting_screen(
                    cap=cap,
                    wait_until=wait_until
                )

                if not ok:
                    break

                state = STATE_READY
                continue

            ret, frame = cap.read()

            if not ret:
                print("อ่านภาพจากกล้องไม่ได้")
                break

            faces = face_app.get(frame)

            if len(faces) == 1:
                face = faces[0]
                det_score = float(face.det_score)

                info_text = f"det_score: {det_score:.3f}"

                draw_face(
                    frame,
                    face,
                    info_text
                )

                cv2.putText(
                    frame,
                    "SCANNING...",
                    (30, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2
                )

                if det_score >= DET_SCORE_THRESHOLD:
                    embedding = face.embedding

                    result = save_or_update_queue(
                        embedding=embedding,
                        det_score=det_score
                    )

                    if result.get("can_print"):
                        fake_print_ticket(result)
                    else:
                        print("")
                        print("ไม่พิมพ์บัตรซ้ำ เพราะใบหน้านี้เคยพิมพ์บัตรแล้ว")
                        print("QUEUE NO:", result.get("queue_no"))

                        if "similarity" in result:
                            print("SIMILARITY:", round(result["similarity"], 4))

                        print("")

                    state = STATE_WAITING

            elif len(faces) > 1:
                cv2.putText(
                    frame,
                    "More than 1 face",
                    (30, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2
                )

            else:
                cv2.putText(
                    frame,
                    "No face",
                    (30, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    2
                )

            cv2.putText(
                frame,
                "Press ESC to exit",
                (30, frame.shape[0] - 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2
            )

            cv2.imshow(WINDOW_NAME, frame)

            if check_exit_key():
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("ปิดระบบแล้ว")


if __name__ == "__main__":
    main()