# shared_state.py

import threading
from datetime import datetime
from config import MAX_QUEUE

state_lock = threading.Lock()

def format_today_thai():
    dt = datetime.now()
    return dt.strftime("%d/%m/") + str(dt.year + 543)

max_queue = MAX_QUEUE
max_queue_from = "default"
api_id = ""
queue_date = datetime.now().strftime("%Y-%m-%d")
queue_date_display = format_today_thai()
api_state = "offline"
checked_at = ""
checked_at_from = "local_machine"
disabled_today = False
enable_time = True
enable_start_time = ""
enable_end_time = ""
enable_time_display = ""
disabled_reason = ""

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
    "max_queue_from": max_queue_from,
    "api_id": api_id,
    "used_queue": 0,
    "queue_date": queue_date,
    "queue_date_display": queue_date_display,

    "api_state": api_state,
    "checked_at": checked_at,
    "checked_at_from": checked_at_from,
    "disabled_today" : disabled_today,

    "enable_time": enable_time,
    "enable_start_time": enable_start_time,
    "enable_end_time": enable_end_time,
    "enable_time_display": enable_time_display,
    "disabled_reason": disabled_reason,
    
    "last_update": ""
}

latest_frame = None
