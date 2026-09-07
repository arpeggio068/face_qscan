# app.py

import threading
import time

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from db import init_db
from api.routes import router
from camera_worker import camera_loop
from config import BASE_DIR, CALL_API_INTERVAL

import shared_state
from queue_config_service import get_queue_config
from queue_service import reset_live_queues_on_test


def apply_queue_config(queue_config):
    disabled_today = queue_config.get("disabled_today", False)

    with shared_state.state_lock:
        shared_state.max_queue = queue_config["max_queue"]
        shared_state.api_id = queue_config.get("api_id", shared_state.api_id)
        shared_state.queue_date = queue_config["queue_date"]
        shared_state.queue_date_display = queue_config["queue_date_display"]
        shared_state.checked_at = queue_config["checked_at"]
        shared_state.api_state = queue_config["api_state"]
        shared_state.disabled_today = disabled_today
        shared_state.enable_time = queue_config["enable_time"]
        shared_state.enable_start_time = queue_config["enable_start_time"]
        shared_state.enable_end_time = queue_config["enable_end_time"]
        shared_state.enable_time_display = queue_config["enable_time_display"]
        shared_state.disabled_reason = queue_config["disabled_reason"]

        shared_state.current_state["max_queue"] = queue_config["max_queue"]
        shared_state.current_state["api_id"] = shared_state.api_id
        shared_state.current_state["queue_date"] = queue_config["queue_date"]
        shared_state.current_state["queue_date_display"] = queue_config["queue_date_display"]
        shared_state.current_state["checked_at"] = queue_config["checked_at"]
        shared_state.current_state["api_state"] = queue_config["api_state"]
        shared_state.current_state["disabled_today"] = disabled_today
        shared_state.current_state["enable_time"] = queue_config["enable_time"]
        shared_state.current_state["enable_start_time"] = queue_config["enable_start_time"]
        shared_state.current_state["enable_end_time"] = queue_config["enable_end_time"]
        shared_state.current_state["enable_time_display"] = queue_config["enable_time_display"]
        shared_state.current_state["disabled_reason"] = queue_config["disabled_reason"]


def queue_config_loop():
    while True:
        time.sleep(CALL_API_INTERVAL) # 300 = 5 นาที

        queue_config = get_queue_config()        

        apply_queue_config(queue_config)

        print(f"[Queue API Update] max_queue = {shared_state.max_queue}")
        print(f"[Queue API Update] checked_at = {shared_state.checked_at}")
        print(f"[Queue API Update] api_state = {shared_state.api_state}")
        print(f"[Queue API Update] disabled_today = {shared_state.disabled_today}")


app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)

templates = Jinja2Templates(directory=BASE_DIR / "templates")

app.include_router(router)


@app.on_event("startup")
def startup_event():
    init_db()

    queue_config = get_queue_config()

    '''
      reset_live_queues_on_test(
              queue_config.get("checked_at")
          )
    '''    

    apply_queue_config(queue_config)

    print(f"[STARTUP] max_queue = {shared_state.max_queue}")
    print(f"[STARTUP] queue_date_display = {shared_state.queue_date_display}")
    print(f"[STARTUP] checked_at = {shared_state.checked_at}")
    print(f"[STARTUP] api_state = {shared_state.api_state}")
    print(f"[STARTUP] disabled_today = {shared_state.disabled_today}")

    t_api = threading.Thread(
        target=queue_config_loop,
        daemon=True
    )
    t_api.start()

    t_camera = threading.Thread(
        target=camera_loop,
        daemon=True
    )
    t_camera.start()


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=False
    )
