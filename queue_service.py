# queue_service.py

import uuid
import numpy as np
from datetime import date, datetime

from db import get_conn
from crypto_service import encrypt_bytes, decrypt_bytes
from face_engine import cosine_similarity
import shared_state
from config import (
    MAX_PRINT_PER_FACE,
    SIMILARITY_THRESHOLD,   
)

from print_service import print_queue_ticket


def now_th():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def embedding_to_blob(embedding):
    raw = embedding.astype(np.float32).tobytes()
    return encrypt_bytes(raw)


def blob_to_embedding(blob):
    raw = decrypt_bytes(blob)
    return np.frombuffer(raw, dtype=np.float32)


def get_today():
    return date.today().isoformat()


def get_next_queue_no(conn, queue_date):
    cur = conn.cursor()

    cur.execute("""
        SELECT queue_no
        FROM queues
        WHERE queue_date = ?
        ORDER BY queue_no DESC
        LIMIT 1
    """, (queue_date,))

    row = cur.fetchone()

    if row is None:
        next_no = 1
    else:
        next_no = int(row[0]) + 1

    max_queue = shared_state.max_queue

    if next_no > max_queue:
        return None

    return f"{next_no:03d}"


def find_similar_face(conn, embedding):
    cur = conn.cursor()
    queue_date = get_today()

    cur.execute("""
        SELECT id, queue_no, face_embedding, print_count, qr_token
        FROM queues
        WHERE queue_date = ?
    """, (queue_date,))

    rows = cur.fetchall()

    best_row = None
    best_similarity = -1

    for row in rows:
        queue_id, queue_no, blob, print_count, qr_token = row

        try:
            old_embedding = blob_to_embedding(blob)
        except Exception as e:
            print(f"Decrypt embedding error queue_id={queue_id}: {e}")
            continue

        sim = cosine_similarity(old_embedding, embedding)

        print(
            f"[FACE CHECK] queue_no={queue_no}, "
            f"similarity={sim:.4f}, "
            f"threshold={SIMILARITY_THRESHOLD}"
        )

        if sim > best_similarity:
            best_similarity = sim
            best_row = {
                "id": queue_id,
                "queue_no": queue_no,
                "print_count": print_count,
                "qr_token": qr_token,
                "similarity": sim
            }

    if best_row and best_similarity >= SIMILARITY_THRESHOLD:
        return best_row

    return None


def insert_log(cur, queue_id, action, similarity=None):
    cur.execute("""
        INSERT INTO queue_logs(queue_id, action, similarity, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        queue_id,
        action,
        similarity,
        now_th()
    ))


def insert_queue_history(cur, queue_date, queue_no, qr_token, det_score, created_at):
    cur.execute("""
        INSERT OR IGNORE INTO queue_history(
            queue_date,
            queue_no,
            qr_token,
            det_score,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        queue_date,
        queue_no,
        qr_token,
        float(det_score),
        created_at
    ))


def save_or_update_queue(embedding, det_score):
    conn = get_conn()
    cur = conn.cursor()
    queue_date = get_today()

    similar = find_similar_face(conn, embedding)

    if similar:
        queue_id = similar["id"]
        queue_no = similar["queue_no"]
        qr_token = similar["qr_token"]
        print_count = similar["print_count"]
        similarity = similar["similarity"]

        if print_count >= MAX_PRINT_PER_FACE:
            action = "same_face_no_print"
            can_print = False

            cur.execute("""
                UPDATE queues
                SET scan_count = scan_count + 1,
                    last_scan_at = ?
                WHERE id = ?
            """, (
                now_th(),
                queue_id
            ))

        else:
            action = "same_face_print"
            can_print = True

            cur.execute("""
                UPDATE queues
                SET print_count = print_count + 1,
                    scan_count = scan_count + 1,
                    last_scan_at = ?
                WHERE id = ?
            """, (
                now_th(),
                queue_id
            ))

        insert_log(
            cur=cur,
            queue_id=queue_id,
            action=action,
            similarity=similarity
        )

        conn.commit()
        conn.close()

        if can_print:
            print_queue_ticket(
                queue_no=queue_no,
                token=qr_token
            )

        return {
            "status": "same_face",
            "queue_id": queue_id,
            "queue_no": queue_no,
            "qr_token": qr_token,
            "similarity": similarity,
            "can_print": can_print,
            "message": "พบใบหน้าเดิม"
        }

    queue_no = get_next_queue_no(conn, queue_date)

    if queue_no is None:
        conn.close()
        return {
            "status": "queue_full",
            "message": "คิวเต็มแล้ว"
        }

    qr_token = str(uuid.uuid4())
    encrypted_embedding = embedding_to_blob(embedding)
    current_time = now_th()

    cur.execute("""
        INSERT INTO queues(
            queue_date,
            queue_no,
            face_embedding,
            qr_token,
            det_score,
            scan_count,
            print_count,
            created_at,
            last_scan_at
        )
        VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?)
    """, (
        queue_date,
        queue_no,
        encrypted_embedding,
        qr_token,
        float(det_score),
        current_time,
        current_time
    ))

    queue_id = cur.lastrowid

    insert_queue_history(
        cur=cur,
        queue_date=queue_date,
        queue_no=queue_no,
        qr_token=qr_token,
        det_score=det_score,
        created_at=current_time
    )

    insert_log(
        cur=cur,
        queue_id=queue_id,
        action="new_queue_print",
        similarity=None
    )    

    conn.commit()
    conn.close()

    try:
        print_queue_ticket(
            queue_no=queue_no,
            token=qr_token
        )
    except Exception as e:
        print("[PRINT ERROR]", e)

    return {
        "status": "new_face",
        "queue_id": queue_id,
        "queue_no": queue_no,
        "qr_token": qr_token,
        "can_print": True,
        "message": "ออกคิวใหม่"
    }


def get_queue_count():
    queue_date = get_today()

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*)
        FROM queues
        WHERE queue_date = ?
    """, (queue_date,))

    count = cur.fetchone()[0]

    conn.close()

    return count



def reset_live_queues():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM queues")

    cur.execute("""
        DELETE FROM sqlite_sequence
        WHERE name = 'queues'
    """)

    conn.commit()
    conn.close()