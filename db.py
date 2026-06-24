import sqlite3
from config import DB_PATH, DATA_DIR


def get_conn():
    DATA_DIR.mkdir(exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS queues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_date TEXT NOT NULL,
            queue_no TEXT NOT NULL,
            face_embedding BLOB NOT NULL,
            qr_token TEXT NOT NULL UNIQUE,
            det_score REAL,
            scan_count INTEGER DEFAULT 1,
            print_count INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            last_scan_at TEXT NOT NULL,           
            UNIQUE(queue_date, queue_no)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS queue_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_date TEXT NOT NULL,
            queue_no TEXT NOT NULL,
            qr_token TEXT NOT NULL,
            det_score REAL,
            created_at TEXT NOT NULL,
            UNIQUE(queue_date, queue_no)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS queue_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            similarity REAL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()