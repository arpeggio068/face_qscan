import threading
from datetime import datetime
from config import MAX_QUEUE

state_lock = threading.Lock()

def format_today_thai():
    dt = datetime.now()
    return dt.strftime("%d/%m/") + str(dt.year + 543)

max_queue = MAX_QUEUE
queue_date = datetime.now().strftime("%Y-%m-%d")
queue_date_display = format_today_thai()
api_state = "offline"
checked_at = ""

current_state = {
    "state": "STARTUP",
    "message": "กำลังเริ่มระบบ",
    "queue_no": "",
    "det_score": 0.0,
    "similarity": None,
    "can_print": False,
    "last_event_id": 0,
    "wait_remaining": 0,
    "video_enabled": False,
    "max_queue": MAX_QUEUE,
    "used_queue": 0,
    "queue_date": queue_date,
    "queue_date_display": queue_date_display,
    "api_state": api_state,
    "checked_at": checked_at,
    "last_update": ""
}

latest_frame = None