from threading import Lock

state_lock = Lock()

current_state = {
    "state": "STARTUP",
    "message": "กำลังเริ่มระบบ",
    "queue_no": "",
    "det_score": 0.0,
    "similarity": None,
    "can_print": False,
    "last_event_id": 0,
    "last_update": ""
}

latest_frame = None