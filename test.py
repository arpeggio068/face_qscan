import cv2
import numpy as np
import sqlite3
from pathlib import Path
from insightface.app import FaceAnalysis


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "test.db"


def test_buff_s():
    app = FaceAnalysis(
        name="buffalo_s",
        providers=["CPUExecutionProvider"]
    )

    app.prepare(ctx_id=0, det_size=(640, 640))

    print("✅ InsightFace OK")
    return app


def test_sqlite():
    DATA_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
    """)

    cursor.execute("INSERT INTO test(name) VALUES (?)", ("sqlite_test",))
    conn.commit()

    cursor.execute("SELECT id, name FROM test ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()

    conn.close()

    print("✅ SQLite OK:", row)


def cosine_similarity(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def test_camera_and_face(app):
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

    if not cap.isOpened():
        print("❌ เปิดกล้องไม่ได้")
        return

    print("✅ Webcam OK")
    print("กด S เพื่อ scan ใบหน้า")
    print("กด Q เพื่อออก")

    last_embedding = None

    while True:
        ret, frame = cap.read()

        if not ret:
            print("❌ อ่านภาพจากกล้องไม่ได้")
            break

        faces = app.get(frame)

        for face in faces:
            x1, y1, x2, y2 = face.bbox.astype(int)

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                "Face Detected",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

        cv2.imshow("Face Queue Test", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        if key == ord("s"):
            if len(faces) == 0:
                print("❌ ไม่พบใบหน้า")
                continue

            if len(faces) > 1:
                print("⚠️ พบมากกว่า 1 ใบหน้า กรุณาให้เหลือ 1 คน")
                continue

            embedding = faces[0].embedding.astype(np.float32)

            print("✅ Scan OK")
            print("Embedding shape:", embedding.shape)
            print("Embedding sample:", embedding[:5])

            if last_embedding is not None:
                sim = cosine_similarity(last_embedding, embedding)
                print("Similarity กับ scan ก่อนหน้า:", round(sim, 4))

            last_embedding = embedding

    cap.release()
    cv2.destroyAllWindows()




def main():
    print("========== TEST START ==========")

    app = test_buff_s()

    test_sqlite()

    test_camera_and_face(app)

    print("========== TEST END ==========")


if __name__ == "__main__":
    main()




# python -c "import win32print; print(win32print.GetDefaultPrinter())" สำหรับตรวจสอบชื่อเครื่อง print