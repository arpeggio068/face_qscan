# queue_update_service.py

import json
import requests

import shared_state
from config import (
    WEB_API_URL,
    QUEUE_UPDATE_INTERVAL,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID,
)


def get_check_time_state():
    with shared_state.state_lock:
        return {
            "checked_at": shared_state.checked_at,
            "checked_at_from": shared_state.checked_at_from,
            "max_queue": int(shared_state.max_queue or 0),
            "max_queue_from": shared_state.max_queue_from,
        }


def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] skipped: token or chat_id not configured")
        return False
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            params={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
            },
            timeout=(5, 10),
        )
        success = response.ok
        print(f"[Telegram] status={'success' if success else 'failed'}, http_status={response.status_code}")
        return success
    except Exception as e:
        print(f"[Telegram] status=failed, error={repr(e)}")
        return False


def send_face_scan_start(checked_at, checked_at_from, max_queue, max_queue_from):
    message = (
        "Face Scan Start\n"
        f"max_queue: {max_queue}\n"
        f"max_queue_from: {max_queue_from}\n"
        f"check_at: {checked_at}\n"
        f"check_at_from: {checked_at_from}"
    )
    return send_telegram(message)


def send_face_scan_update(queue_no):
    state = get_check_time_state()
    message = (
        "Face Scan Update\n"
        f"last_queue: {int(queue_no)}\n"
        f"max_queue: {state['max_queue']}\n"
        f"max_queue_from: {state['max_queue_from']}\n"
        f"check_at: {state['checked_at']}\n"
        f"check_at_from: {state['checked_at_from']}"
    )
    return send_telegram(message)


def get_update_state():
    with shared_state.state_lock:
        return {
            "api_id": str(shared_state.api_id or "").strip(),
            "max_queue": int(shared_state.max_queue or 0),
        }


def should_update_queue(queue_no, max_queue):
    try:
        queue_no = int(queue_no)
        interval = int(QUEUE_UPDATE_INTERVAL)
    except (TypeError, ValueError):
        return False
    if queue_no <= 0 or max_queue <= 0 or interval <= 0:
        return False
    return queue_no % interval == 0 or queue_no == max_queue


def post_latest_queue_if_due(queue_no):
    state = get_update_state()
    api_id = state["api_id"]
    max_queue = state["max_queue"]

    if not should_update_queue(queue_no, max_queue):
        return False
    send_face_scan_update(queue_no)
    if not WEB_API_URL:
        print("[Queue POST] skipped: WEB_API_URL not configured")
        return False
    if not api_id:
        print(f"[Queue POST] skipped: no api_id, queue_no={queue_no}")
        return False

    payload = {
        "action": "updateQueue",
        "data": json.dumps({
            "id": api_id,
            "last_queue": int(queue_no),
        }),
    }

    try:
        response = requests.post(
            WEB_API_URL,
            data=payload,
            timeout=(10, 30),
            allow_redirects=True,
        )
        response.raise_for_status()
        result = response.json()
        if result.get("res_status") is not True:
            raise ValueError(result.get("message", "API update failed"))
        print(f"[Queue POST] success: api_id={api_id}, last_queue={queue_no}")
        return True
    except Exception as e:
        print(f"[Queue POST] failed: queue_no={queue_no}, error={repr(e)}")
        return False
