# queue_config_service.py
import requests
from datetime import datetime
import shared_state
from config import MAX_QUEUE, WEB_API_URL, ENABLE_START_TIME, ENABLE_END_TIME

_queues_reset_done = False

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

def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def today_text():
    return datetime.now().strftime("%Y-%m-%d")

def normalize_checked_at(checked_at=None):
    api_dt = parse_checked_at(checked_at)
    return api_dt.strftime("%Y-%m-%d %H:%M:%S") if api_dt is not None else now_text()

def set_global_api_id(api_id):
    with shared_state.state_lock:
        shared_state.api_id = api_id
        shared_state.current_state["api_id"] = api_id

def update_api_id(reason, data):
    if reason != "queue_data_found" or not isinstance(data, list) or not data or not isinstance(data[0], dict):
        return shared_state.api_id
    api_id = str(data[0].get("api_id", "")).strip()
    if not api_id:
        print("[Queue API] response has no api_id, keep previous api_id")
        return shared_state.api_id
    set_global_api_id(api_id)
    print(f"[Queue API] api_id = {api_id}")
    return api_id

def is_enable_time(checked_at=None, time_source=None):
    api_dt = parse_checked_at(checked_at)
    if api_dt is not None:
        check_time = api_dt.time()
        time_source = time_source or "api_checked_at"
    else:
        check_time = datetime.now().time()
        time_source = "local_machine"
    enable_time = parse_time(ENABLE_START_TIME) <= check_time <= parse_time(ENABLE_END_TIME)
    print(f"[Queue Time] check_time = {check_time.strftime('%H:%M:%S')}")
    print(f"[Queue Time] time_source = {time_source}")
    print(f"[Queue Time] enable_time = {enable_time}")
    return enable_time

def enable_time_display():
    return f"เวลารับคิว {ENABLE_START_TIME} น. ถึง {ENABLE_END_TIME} น."

def is_weekend(checked_at=None):
    check_dt = parse_checked_at(checked_at) or datetime.now()
    return check_dt.weekday() in (5, 6)

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
    use_api_time = parse_checked_at(checked_at) is not None
    checked_at = normalize_checked_at(checked_at)
    default_date = checked_at[:10]
    return {
        "max_queue": MAX_QUEUE,
        "queue_date": default_date,
        "queue_date_display": format_thai_date(default_date),
        "checked_at": checked_at,
        "api_id": shared_state.api_id,
        "api_state": "offline",
        "source": "default",
        "reason": "default_config",
        "disabled_today": False,
        "enable_time": is_enable_time(checked_at, "api_checked_at" if use_api_time else "local_machine"),
        "enable_start_time": ENABLE_START_TIME,
        "enable_end_time": ENABLE_END_TIME,
        "enable_time_display": enable_time_display(),
        "disabled_reason": ""
    }

def apply_disable(result, disabled_reason):
    result["disabled_today"] = True
    result["max_queue"] = 0
    result["disabled_reason"] = disabled_reason
    return result

def apply_runtime_disable(result, api_disabled=False):
    disabled_reason = get_disabled_reason(api_disabled, is_weekend(result["checked_at"]), not result["enable_time"])
    if disabled_reason:
        apply_disable(result, disabled_reason)
    return result

def get_cached_or_default_result(checked_at=None):
    from queue_service import load_queue_config_cache
    result = base_result(checked_at)
    try:
        cache = load_queue_config_cache(result["checked_at"][:10])
    except Exception as e:
        print(f"[Queue Cache] load error = {repr(e)}")
        cache = None
    if not cache:
        print(f"[Queue Cache] not found, use default max_queue = {result['max_queue']}")
        return result
    set_global_api_id(cache["api_id"])
    result.update({
        "api_id": cache["api_id"],
        "queue_date": cache["queue_date"],
        "queue_date_display": format_thai_date(cache["queue_date"]),
        "max_queue": cache["max_queue"],
        "source": "cache",
        "reason": "queue_cache_found"
    })
    print(f"[Queue Cache] loaded max_queue = {cache['max_queue']}")
    return result

def finalize_queue_config(result):
    global _queues_reset_done
    if not _queues_reset_done:
        from queue_service import reset_live_queues
        reset_live_queues(result["checked_at"])
        _queues_reset_done = True
    return result

def get_queue_config():
    print("========== Queue API ==========")
    if not WEB_API_URL:
        print("[Queue API] WEB_API_URL not configured")
        return finalize_queue_config(apply_runtime_disable(get_cached_or_default_result()))
    try:
        print("[Queue API] calling api...")
        r = requests.get(WEB_API_URL, timeout=(10, 30))
        print(f"[Queue API] HTTP Status = {r.status_code}")
        print(f"[Queue API] Response = {r.text[:500]}")
        r.raise_for_status()
        obj = r.json()
        checked_at = normalize_checked_at(obj.get("checked_at"))
        reason = obj.get("reason", "")
        data = obj.get("data", [])
        api_disabled = bool(obj.get("disabled_today", False))
        valid_data = obj.get("status") is True and reason == "queue_data_found" and isinstance(data, list) and data and isinstance(data[0], dict)
        if not valid_data:
            if api_disabled:
                result = get_cached_or_default_result(checked_at)
                result.update({"checked_at": checked_at, "api_state": "online", "source": "api", "reason": reason or "api_disabled"})
                return finalize_queue_config(apply_runtime_disable(result, api_disabled=True))
            raise ValueError(f"invalid queue config: status={obj.get('status')}, reason={reason}, data={data}")
        rec = data[0]
        api_id = update_api_id(reason, data)
        queue_date = rec.get("queue_date", checked_at[:10])
        max_queue = int(rec.get("max_queue"))
        result = base_result(checked_at)
        result.update({
            "max_queue": max_queue,
            "queue_date": queue_date,
            "queue_date_display": format_thai_date(queue_date),
            "checked_at": checked_at,
            "api_id": api_id,
            "api_state": "online",
            "source": "api",
            "reason": reason,
            "disabled_today": False,
            "disabled_reason": ""
        })
        from queue_service import save_queue_config_cache
        save_queue_config_cache(result)
        print(f"[Queue Cache] saved max_queue = {max_queue}")
        apply_runtime_disable(result, api_disabled=api_disabled)
        print(f"[Queue API] MAX_QUEUE = {max_queue}")
        print(f"[Queue API] queue_date = {queue_date}")
        print(f"[Queue API] checked_at = {checked_at}")
        print(f"[Queue API] disabled_today = {result['disabled_today']}")
        print(f"[Queue API] disabled_reason = {result['disabled_reason']}")
        return finalize_queue_config(result)
    except Exception as e:
        print(f"[Queue API] Exception = {repr(e)}")
    result = apply_runtime_disable(get_cached_or_default_result())
    print(f"[Queue API] fallback source = {result['source']}")
    print(f"[Queue API] fallback MAX_QUEUE = {result['max_queue']}")
    print(f"[Queue API] disabled_today = {result['disabled_today']}")
    print(f"[Queue API] disabled_reason = {result['disabled_reason']}")
    return finalize_queue_config(result)
