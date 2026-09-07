# queue_update_service.py

import json
import requests

import shared_state
from config import WEB_API_URL, QUEUE_UPDATE_INTERVAL


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

        print(f"[Queue POST] HTTP Status = {response.status_code}")
        print(f"[Queue POST] History = {[r.status_code for r in response.history]}")
        print(f"[Queue POST] Final URL = {response.url}")
        print(f"[Queue POST] Content-Type = {response.headers.get('content-type')}")
        print(f"[Queue POST] Response = {repr(response.text[:500])}")

        response.raise_for_status()

        if not response.text.strip():
            raise ValueError("API returned empty response")

        result = response.json()

        if result.get("res_status") is not True:
            raise ValueError(result.get("message", "API update failed"))

        print(
            f"[Queue POST] success: "
            f"api_id={api_id}, last_queue={queue_no}"
        )
        return True

    except Exception as e:
        print(
            f"[Queue POST] failed: "
            f"queue_no={queue_no}, error={repr(e)}"
        )
        return False
