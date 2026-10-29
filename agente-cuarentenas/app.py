import os
import re
import secrets
import threading
import time
import traceback
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

import agent
import db

app = FastAPI()
security = HTTPBasic()
STATE = {"last_run": None, "next_run": None, "running": False, "last_error": None}
_lock = threading.Lock()
INTERVAL = int(os.environ.get("INTERVAL_MIN", "15"))


def auth(c: HTTPBasicCredentials = Depends(security)):
    ok = (secrets.compare_digest(c.username, os.environ["DASHBOARD_USER"])
          and secrets.compare_digest(c.password, os.environ["DASHBOARD_PASSWORD"]))
    if not ok:
        raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})


def run_once():
    if not _lock.acquire(blocking=False):
        return
    STATE["running"] = True
    try:
        agent.run_all()
        STATE["last_error"] = None
    except Exception as e:
        traceback.print_exc()
        STATE["last_error"] = f"{type(e).__name__}: {e}"
    finally:
        STATE["last_run"] = datetime.now(timezone.utc).isoformat()
        STATE["running"] = False
        _lock.release()


def loop():
    while True:
        run_once()
        STATE["next_run"] = datetime.fromtimestamp(time.time() + INTERVAL * 60, timezone.utc).isoformat()
        time.sleep(INTERVAL * 60)


@app.on_event("startup")
def startup():
    db.init()
    threading.Thread(target=loop, daemon=True).start()


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/")
def index(_=Depends(auth)):
    return FileResponse("static/index.html")


@app.get("/api/status")
def status(_=Depends(auth)):
    return {**STATE, "mode": agent.MODE, "interval_min": INTERVAL}


@app.get("/api/logs")
def logs(_=Depends(auth)):
    return db.recent(500)


@app.get("/debug/{name}")
def debug(name: str, _=Depends(auth)):
    if not re.fullmatch(r"[a-z0-9-]+\.(png|txt)", name):
        raise HTTPException(404)
    path = f"/data/debug/{name}"
    if not os.path.exists(path):
        raise HTTPException(404)
    return FileResponse(path)
