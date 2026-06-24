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

    t = threading.Thread(
        target=camera_loop,
        daemon=True
    )
    t.start()


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