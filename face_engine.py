import cv2
import numpy as np
from insightface.app import FaceAnalysis
from config import FACE_MODEL_NAME


def load_face_app():
    app = FaceAnalysis(
        name=FACE_MODEL_NAME,
        providers=["CPUExecutionProvider"]
    )

    app.prepare(ctx_id=0, det_size=(640, 640))
    return app


def cosine_similarity(a, b):
    return float(
        np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    )


def draw_face(frame, face, text="Face"):
    x1, y1, x2, y2 = face.bbox.astype(int)

    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    cv2.putText(
        frame,
        text,
        (x1, y1 - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )