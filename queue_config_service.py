# queue_config_service.py

import requests
from datetime import datetime

from config import (
    MAX_QUEUE,
    WEB_API_URL,
    ENABLE_START_TIME,
    ENABLE_END_TIME,
)


def parse_time(time_text):
    return datetime.strptime(time_text, "%H:%M").time()


def parse_checked_at(checked_at):
    try:
        if not checked_at:
            return None

        return datetime.strptime(checked_at, "%Y-%m-%d %H:%M:%S")

    except Exception as e:
        print(f"[Queue Time] parse checked_at error = {repr(e)}")
        return None


def is_enable_time(checked_at=None):
    api_dt = parse_checked_at(checked_at)

    if api_dt is not None:
        check_time = api_dt.time()
        time_source = "api_checked_at"
        print(f"[Queue Time] use API checked_at = {checked_at}")
    else:
        check_time = datetime.now().time()
        time_source = "local_machine"
        print(f"[Queue Time] use local machine time = {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = parse_time(ENABLE_START_TIME)
    end_time = parse_time(ENABLE_END_TIME)

    enable_time = start_time <= check_time <= end_time

    print(f"[Queue Time] ENABLE_START_TIME = {ENABLE_START_TIME}")
    print(f"[Queue Time] ENABLE_END_TIME = {ENABLE_END_TIME}")
    print(f"[Queue Time] check_time = {check_time.strftime('%H:%M:%S')}")
    print(f"[Queue Time] time_source = {time_source}")
    print(f"[Queue Time] enable_time = {enable_time}")

    return enable_time


def enable_time_display():
    return f"เวลารับคิว {ENABLE_START_TIME} น. ถึง {ENABLE_END_TIME} น."


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_text():
    return datetime.now().strftime("%Y-%m-%d")


def is_weekend():
    # mon = 0, tue = 1, wed = 2, thu = 3, fri = 4, sat = 5, sun = 6
    return datetime.now().weekday() in (5, 6)


def get_disabled_reason(api_disabled, weekend_disabled, time_disabled):
    if api_disabled:
        return "api_disabled"
    if weekend_disabled:
        return "weekend"
    if time_disabled:
        return "out_of_service_time"
    return ""


def format_thai_date(date_str):
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%d/%m/") + str(dt.year + 543)
    except Exception:
        dt = datetime.now()
        return dt.strftime("%d/%m/") + str(dt.year + 543)


def base_result(checked_at=None):
    default_date = today_text()
    enable_time = is_enable_time(checked_at)

    return {
        "max_queue": MAX_QUEUE,
        "queue_date": default_date,
        "queue_date_display": format_thai_date(default_date),
        "checked_at": checked_at or now_text(),
        "api_state": "offline",
        "source": "default",
        "disabled_today": False,

        "enable_time": enable_time,
        "enable_start_time": ENABLE_START_TIME,
        "enable_end_time": ENABLE_END_TIME,
        "enable_time_display": enable_time_display(),
        "disabled_reason": "",
    }


def apply_disable(result, disabled_reason):
    result["disabled_today"] = True
    result["max_queue"] = 0
    result["disabled_reason"] = disabled_reason
    return result


def get_queue_config():
    default_date = today_text()
    result = base_result()

    enable_time = result["enable_time"]
    weekend_disabled = is_weekend()
    time_disabled = not enable_time

    print("========== Queue API ==========")

    if not WEB_API_URL:
        print("[Queue API] WEB_API_URL not configured")

        disabled_reason = get_disabled_reason(
            api_disabled=False,
            weekend_disabled=weekend_disabled,
            time_disabled=time_disabled
        )

        if disabled_reason:
            apply_disable(result, disabled_reason)
            print(f"[Queue API] disabled_reason = {disabled_reason}")

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

        api_disabled = bool(obj.get("disabled_today", False))
        weekend_disabled = is_weekend()
        enable_time = is_enable_time(checked_at)
        time_disabled = not enable_time

        disabled_reason = get_disabled_reason(
            api_disabled=api_disabled,
            weekend_disabled=weekend_disabled,
            time_disabled=time_disabled
        )

        disabled_today = disabled_reason != ""

        if disabled_today:
            result = base_result(checked_at)
            result["checked_at"] = checked_at
            result["api_state"] = "online"
            result["source"] = "api"

            apply_disable(result, disabled_reason)

            print("[Queue API] disabled_today = True")
            print(f"[Queue API] disabled_reason = {disabled_reason}")
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

                result = base_result(checked_at)
                result.update({
                    "max_queue": max_queue,
                    "queue_date": queue_date,
                    "queue_date_display": format_thai_date(queue_date),
                    "checked_at": checked_at,
                    "api_state": "online",
                    "source": "api",
                    "disabled_today": False,
                    "disabled_reason": "",
                })

                print(f"[Queue API] MAX_QUEUE = {max_queue}")
                print(f"[Queue API] queue_date = {queue_date}")
                print(f"[Queue API] checked_at = {result['checked_at']}")
                print("[Queue API] api_state = online")
                print("[Queue API] disabled_today = False")
                print(f"[Queue API] enable_time = {result['enable_time']}")
                print(f"[Queue API] enable_time_display = {result['enable_time_display']}")

                return result

        # API สำเร็จ แต่ status=false หรือ data ว่าง
        # ยังใช้ checked_at จาก API ในการเช็คเวลา
        print("[Queue API] status false or data empty")

        result = base_result(checked_at)
        result["checked_at"] = checked_at
        result["api_state"] = "online"
        result["source"] = "api"

        weekend_disabled = is_weekend()
        time_disabled = not result["enable_time"]

        disabled_reason = get_disabled_reason(
            api_disabled=False,
            weekend_disabled=weekend_disabled,
            time_disabled=time_disabled
        )

        if disabled_reason:
            apply_disable(result, disabled_reason)

        print(f"[Queue API] checked_at = {checked_at}")
        print("[Queue API] api_state = online")
        print(f"[Queue API] disabled_today = {result['disabled_today']}")
        print(f"[Queue API] disabled_reason = {result['disabled_reason']}")
        print(f"[Queue API] enable_time = {result['enable_time']}")
        print(f"[Queue API] enable_time_display = {result['enable_time_display']}")

        return result

    except Exception as e:
        print(f"[Queue API] Exception = {repr(e)}")

    # API ใช้งานไม่ได้จริง ๆ จึง fallback ใช้เวลาเครื่อง
    result = base_result()

    weekend_disabled = is_weekend()
    time_disabled = not result["enable_time"]

    disabled_reason = get_disabled_reason(
        api_disabled=False,
        weekend_disabled=weekend_disabled,
        time_disabled=time_disabled
    )

    if disabled_reason:
        apply_disable(result, disabled_reason)

    print(f"[Queue API] use default MAX_QUEUE = {result['max_queue']}")
    print("[Queue API] api_state = offline")
    print(f"[Queue API] disabled_today = {result['disabled_today']}")
    print(f"[Queue API] disabled_reason = {result['disabled_reason']}")
    print(f"[Queue API] enable_time = {result['enable_time']}")
    print(f"[Queue API] enable_time_display = {result['enable_time_display']}")

    return result