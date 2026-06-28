# queue_config_service.py

import requests
from datetime import datetime

from config import (
    MAX_QUEUE,
    WEB_API_URL,
)


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_text():
    return datetime.now().strftime("%Y-%m-%d")


def format_thai_date(date_str):
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%d/%m/") + str(dt.year + 543)
    except Exception:
        dt = datetime.now()
        return dt.strftime("%d/%m/") + str(dt.year + 543)


def get_queue_config():
    default_date = today_text()

    result = {
        "max_queue": MAX_QUEUE,
        "queue_date": default_date,
        "queue_date_display": format_thai_date(default_date),
        "checked_at": now_text(),
        "api_state": "offline",
        "source": "default",
        "disabled_today": False,
    }

    print("========== Queue API ==========")
    # print(f"WEB_API_URL = [{WEB_API_URL}]")

    if not WEB_API_URL:
        print("[Queue API] WEB_API_URL not configured")
        return result

    try:
        print("[Queue API] calling api...")

        r = requests.get(
            WEB_API_URL,
            timeout=5
        )

        print(f"[Queue API] HTTP Status = {r.status_code}")
        print(f"[Queue API] Response = {r.text}")

        r.raise_for_status()

        obj = r.json()

        checked_at = obj.get("checked_at", now_text())
        disabled_today = bool(obj.get("disabled_today", False))

        # ถ้าวันนี้ปิดบริการ ไม่สนใจ queue_date / max_queue
        if disabled_today:
            result = {
                "max_queue": 0,
                "queue_date": default_date,
                "queue_date_display": format_thai_date(default_date),
                "checked_at": checked_at,
                "api_state": "online",
                "source": "api",
                "disabled_today": True,
            }

            print("[Queue API] disabled_today = True")
            print("[Queue API] วันนี้งดบริการแจกคิว")
            print(f"[Queue API] checked_at = {checked_at}")
            print("[Queue API] api_state = online")

            return result

        if obj.get("status"):
            data = obj.get("data", [])

            if data:
                rec = data[0]

                queue_date = rec.get("queue_date", default_date)
                max_queue = int(rec.get("max_queue"))

                result = {
                    "max_queue": max_queue,
                    "queue_date": queue_date,
                    "queue_date_display": format_thai_date(queue_date),
                    "checked_at": checked_at,
                    "api_state": "online",
                    "source": "api",
                    "disabled_today": False,
                }

                print(f"[Queue API] MAX_QUEUE = {max_queue}")
                print(f"[Queue API] queue_date = {queue_date}")
                print(f"[Queue API] checked_at = {result['checked_at']}")
                print("[Queue API] api_state = online")
                print("[Queue API] disabled_today = False")

                return result

        print("[Queue API] status false or data empty")

    except Exception as e:
        print(f"[Queue API] Exception = {repr(e)}")

    print(f"[Queue API] use default MAX_QUEUE = {MAX_QUEUE}")
    print("[Queue API] api_state = offline")
    print("[Queue API] disabled_today = False")

    return result