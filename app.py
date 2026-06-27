# app.py

import threading

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from db import init_db
from api.routes import router
from camera_worker import camera_loop
from config import BASE_DIR

import shared_state
from queue_config_service import get_queue_config
import time


def apply_queue_config(queue_config):
    with shared_state.state_lock:
        shared_state.max_queue = queue_config["max_queue"]
        shared_state.queue_date = queue_config["queue_date"]
        shared_state.queue_date_display = queue_config["queue_date_display"]
        shared_state.checked_at = queue_config["checked_at"]
        shared_state.api_state = queue_config["api_state"]

        shared_state.current_state["max_queue"] = queue_config["max_queue"]
        shared_state.current_state["queue_date"] = queue_config["queue_date"]
        shared_state.current_state["queue_date_display"] = queue_config["queue_date_display"]
        shared_state.current_state["checked_at"] = queue_config["checked_at"]
        shared_state.current_state["api_state"] = queue_config["api_state"]


def queue_config_loop():
    while True:
        time.sleep(300)

        queue_config = get_queue_config()
        apply_queue_config(queue_config)

        print(f"[Queue API Update] max_queue = {shared_state.max_queue}")
        print(f"[Queue API Update] checked_at = {shared_state.checked_at}")
        print(f"[Queue API Update] api_state = {shared_state.api_state}")


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
    apply_queue_config(queue_config)

    print(f"[STARTUP] max_queue = {shared_state.max_queue}")
    print(f"[STARTUP] queue_date_display = {shared_state.queue_date_display}")
    print(f"[STARTUP] checked_at = {shared_state.checked_at}")
    print(f"[STARTUP] api_state = {shared_state.api_state}")

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