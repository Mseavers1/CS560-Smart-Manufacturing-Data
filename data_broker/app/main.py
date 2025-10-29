# conda activate data 
# uvicorn main:app --host 0.0.0.0 --port 8000 --reload   --- Server
# mosquitto_sub -h localhost -t "test/topic" -v          --- Broker Listening Test (Don't need with code below)
#    --- Client sends message (Sends the message or info) [test only] -- Devices need code that is shown in client.py

# sudo systemctl start mosquitto -- Do status to see if it is running but if not, start it
# make sure moquitto is not running before building ^^^


# To access db: docker exec -it postgres-db psql -U db_user -d manufacturing_db
# To backup db: docker exec -t postgres-db pg_dump -U db_user -d manufacturing_db > manufacturing_db.sql
# To recover db: cat manufacturing_db.sql | docker exec -i postgres-db psql -U db_user -d manufacturing_db

import asyncio
import json
import platform
import time
from datetime import datetime, timedelta
import psutil
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi_mqtt import FastMQTT, MQTTConfig
import os
from .database import Database
from typing import List, AsyncGenerator, Dict, Any, Optional, Set
from .tcp_server import handle_robot, start_tcp_server
from pathlib import Path
import subprocess
from collections import deque

mqtt_config = MQTTConfig(
    host="host.docker.internal",
    port=1883,
    keepalive=60,
)
app = FastAPI()
mqtt = FastMQTT(config=mqtt_config)
mqtt.init_app(app)

### ------------------------------------------------------ ###

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
START_TIME = datetime.utcnow()

mqtt_event_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
app.state.robot_subscribers: Set[asyncio.Queue] = set()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

async def broadcast_robot_event(message: str):
    """
    Fan-out a text message to all connected robot SSE subscribers.
    Drops oldest entry if a client queue is full to avoid blocking.
    """
    dead = []
    for q in list(app.state.robot_subscribers):
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            try:
                _ = q.get_nowait()  # drop oldest
            except Exception:
                pass
            try:
                q.put_nowait(message)
            except Exception:
                # client likely gone; mark for cleanup
                dead.append(q)
        except Exception:
            dead.append(q)
    for q in dead:
        app.state.robot_subscribers.discard(q)

def fmt_bytes(n: int) -> str:
    # human-readable bytes (B, KB, MB, GB, TB)
    step = 1024.0
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if n < step:
            return f"{n:.2f} {unit}"
        n /= step
    return f"{n:.2f} EB"

def ping(host: str = "8.8.8.8", timeout_ms: int = 800) -> Optional[float]:
    """
    Returns latency in ms if ping succeeds, else None.
    Cross-platform ping using system binary.
    """
    system = platform.system().lower()
    try:
        if system == "windows":
            # -n 1 (one echo request), -w timeout(ms)
            out = subprocess.run(["ping", "-n", "1", "-w", str(timeout_ms), host],
                                 capture_output=True, text=True)
            if out.returncode == 0 and "Average =" in out.stdout:
                # Parse "Average = Xms" (en-US). Fallback: look for "Minimum = Xms, Maximum = Yms, Average = Zms"
                for tok in out.stdout.split():
                    if tok.lower().endswith("ms") and tok[:-2].isdigit():
                        return float(tok[:-2])
                return None
            return None
        else:
            # Linux/macOS: -c 1 (one packet), -W timeout (sec)
            timeout_s = max(1, int(timeout_ms / 1000))
            out = subprocess.run(["ping", "-c", "1", "-W", str(timeout_s), host],
                                 capture_output=True, text=True)
            if out.returncode == 0:
                # look for "time=XX ms"
                for tok in out.stdout.split():
                    if tok.startswith("time=") and tok[5:].replace(".", "", 1).isdigit():
                        return float(tok[5:])
                # fallback: find any "... ms"
                for tok in out.stdout.split():
                    if tok.endswith("ms"):
                        num = tok.replace("ms", "")
                        try:
                            return float(num)
                        except:
                            pass
            return None
    except Exception:
        return None

async def get_session_stats(app) -> Dict[str, Any]:
    try:
        db: Database = app.state.db
        sessions = await db.retrieve_sessions()
        return {
            "count": len(sessions),
            "latest": sessions[-1] if sessions else None
        }
    except Exception as e:
        return {"error": str(e)}

def collect_metrics() -> Dict[str, Any]:
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    now = datetime.utcnow()

    # CPU
    cpu_percent = psutil.cpu_percent(interval=None)
    per_core = psutil.cpu_percent(interval=None, percpu=True)

    # Memory
    vm = psutil.virtual_memory()
    mem = {
        "total": vm.total, "used": vm.used, "free": vm.available, "percent": vm.percent
    }

    # Disk (root)
    disk = psutil.disk_usage("/")
    disk_io = psutil.disk_io_counters(perdisk=False)

    # Network (interfaces)
    net = psutil.net_io_counters(pernic=False)
    per_nic = {
        nic: {
            "bytes_sent": s.bytes_sent,
            "bytes_recv": s.bytes_recv,
            "packets_sent": s.packets_sent,
            "packets_recv": s.packets_recv,
            "errin": s.errin,
            "errout": s.errout,
            "dropin": getattr(s, "dropin", 0),
            "dropout": getattr(s, "dropout", 0),
        }
        for nic, s in psutil.net_io_counters(pernic=True).items()
    }

    # Backups
    backup_dir = Path("/db_backups")
    backups = []
    if backup_dir.exists():
        for file in sorted(backup_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if file.is_file():
                backups.append({
                    "name": file.name,
                    "size": file.stat().st_size,
                    "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat()
                })

    # Active TCP connections (robots, clients, etc.)
    connections = []
    for c in psutil.net_connections(kind='inet'):
        if c.laddr and c.raddr:
            connections.append({
                "local": f"{c.laddr.ip}:{c.laddr.port}",
                "remote": f"{c.raddr.ip}:{c.raddr.port}",
                "status": c.status,
                "pid": c.pid
            })

    # MQTT status
    mqtt_status = {
        "is_connected": getattr(mqtt.client, "is_connected", False),
        "broker_host": mqtt_config.host,
        "broker_port": mqtt_config.port,
        "subscriptions": list(getattr(mqtt, "_subscriptions", {}).keys())
        if hasattr(mqtt, "_subscriptions")
        else [],
    }


    # Ping
    latency_ms = ping()

    return {
        "timestamp": now.isoformat() + "Z",
        "uptime": (now - boot_time).total_seconds(),
        "process_uptime": (now - START_TIME).total_seconds(),
        "cpu": {
            "percent": cpu_percent,
            "per_core": per_core,
            "count_logical": psutil.cpu_count(),
            "count_physical": psutil.cpu_count(logical=False),
            "load_avg": psutil.getloadavg() if hasattr(psutil, "getloadavg") else None,
        },
        "memory": mem,
        "disk": {
            "total": disk.total,
            "used": disk.used,
            "free": disk.free,
            "percent": disk.percent,
            "io": {
                "read_bytes": disk_io.read_bytes,
                "write_bytes": disk_io.write_bytes,
                "read_count": disk_io.read_count,
                "write_count": disk_io.write_count,
            }
        },
        "network": {
            "bytes_sent": net.bytes_sent,
            "bytes_recv": net.bytes_recv,
            "packets_sent": net.packets_sent,
            "packets_recv": net.packets_recv,
            "errin": net.errin,
            "errout": net.errout,
            "dropin": getattr(net, "dropin", None),
            "dropout": getattr(net, "dropout", None),
            "latency_ms": latency_ms,
            "per_nic": per_nic,
        },
        "host": {
            "name": platform.node(),
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "mqtt": mqtt_status,
        "connections": connections,
        "backups": backups,
    }

@app.get("/api/metrics", response_class=JSONResponse)
def api_metrics():
    return collect_metrics()

@app.get("/events/metrics")
async def metrics_sse() -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[bytes, None]:
        last = psutil.net_io_counters()
        last_time = time.time()

        while True:
            data = collect_metrics()

            # Add async DB info
            session_info = await get_session_stats(app)
            data["sessions"] = session_info

            # Network throughput calc
            now_time = time.time()
            delta_t = max(1e-6, now_time - last_time)
            cur = psutil.net_io_counters()
            data["network"]["tx_rate_bps"] = (cur.bytes_sent - last.bytes_sent) * 8 / delta_t
            data["network"]["rx_rate_bps"] = (cur.bytes_recv - last.bytes_recv) * 8 / delta_t
            last, last_time = cur, now_time

            yield f"data: {json.dumps(data)}\n\n".encode("utf-8")
            await asyncio.sleep(2.0)
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/events/robot")
async def robot_event_stream() -> StreamingResponse:
    async def event_stream():
        # per-client queue
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=200)
        app.state.robot_subscribers.add(q)
        try:
            # optional: announce that a client connected
            await q.put(json.dumps({"type": "info", "msg": "robot feed connected", "ts": datetime.utcnow().isoformat()+"Z"}))
            while True:
                msg = await q.get()
                yield f"data: {msg}\n\n".encode("utf-8")
        finally:
            app.state.robot_subscribers.discard(q)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "text/event-stream",
    }
    return StreamingResponse(event_stream(), headers=headers)

@app.get("/events/mqtt")
async def mqtt_event_stream() -> StreamingResponse:
    async def event_stream() -> AsyncGenerator[bytes, None]:
        # When a new client connects, replay last few messages (optional)
        recent: deque[str] = deque(maxlen=20)
        while True:
            try:
                msg = await mqtt_event_queue.get()
                recent.append(msg)
                yield f"data: {msg}\n\n".encode("utf-8")
            except Exception as e:
                yield f"event: error\ndata: {str(e)}\n\n".encode("utf-8")
                await asyncio.sleep(1)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "text/event-stream",
    }
    return StreamingResponse(event_stream(), headers=headers)

### --------------------------------------------------------------------- ###

def try_backup():
  
  try:
    db: Database = app.state.db
    print(db.create_backup(), flush=True)

    return {"status": "ok"}
  except Exception as e:
    print(f"Failed to manually backup: {e}", flush=True)

    raise HTTPException(status_code=500, detail=f"Backup failed: {e}")

@app.get("/backup/list")
def list_backups():

  folder = Path("/db_backups")
  files = []

  # List all files
  for file in folder.iterdir():
    if file.is_file():
      files.append(file.name)
      print(file.name, flush=True)

  return {"files": files}

# Manually backup
@app.get("/backup")
def backup():
  return try_backup()

### This doesn't work
@app.get("/backup/load/{file_name}")
def load_backup(file_name: str):
    try:
        backup_file = Path("/db_backups") / file_name  # this is the mounted host folder
        if not backup_file.exists():
            raise HTTPException(404, detail=f"Backup not found: {backup_file}")

        # env for pg tools
        env = {
            **os.environ,
            "PGHOST": os.environ.get("PGHOST", "database"),
            "PGPORT": os.environ.get("PGPORT", "5432"),
            "PGUSER": os.environ["PGUSER"],
            "PGPASSWORD": os.environ["PGPASSWORD"],
            "PGDATABASE": os.environ["PGDATABASE"],
        }

        # drop & recreate DB to get a clean state
        subprocess.run(
            ["dropdb", "--if-exists", "-h", env["PGHOST"], "-p", env["PGPORT"], "-U", env["PGUSER"], env["PGDATABASE"]],
            check=True, env=env
        )
        subprocess.run(
            ["createdb", "-h", env["PGHOST"], "-p", env["PGPORT"], "-U", env["PGUSER"], env["PGDATABASE"]],
            check=True, env=env
        )

        # restore from .dump
        subprocess.run(
            ["pg_restore", "-h", env["PGHOST"], "-p", env["PGPORT"], "-U", env["PGUSER"], "-d", env["PGDATABASE"], str(backup_file)],
            check=True, env=env
        )

        return {"status": "ok", "restored": file_name}

    except subprocess.CalledProcessError as e:
        raise HTTPException(500, detail=f"restore failed: {e}")
    except Exception as e:
        raise HTTPException(500, detail=str(e))

# Test ping if server is running and recieving
# @app.get("/ping")
# def ping():
#   return {"status": "ok"}

@app.get("/sessions")
async def get_sessions():
  try:
    db: Database = app.state.db
    data = await db.retrieve_sessions()

    return {"data": data, "success": True}
  except Exception as e:
    print(f"Failed to pull sessions: {e}", flush=True)

    return {"error": str(e), "success": False}


@app.get("/imu/{label}")
async def get_imu(label: str):

  try:
    db: Database = app.state.db
    data = await db.retrieve_imu(label)

    return {"data": data, "success": True}
  except Exception as e:
    print(f"Failed to pull imu data from session '{label}': {e}", flush=True)

    return {"error": str(e), "success": False}

@app.get("/camera/{label}")
async def get_camera(label: str):

  try:
    db: Database = app.state.db
    data = await db.retrieve_camera(label)

    return {"data": data, "success": True}
  except Exception as e:
    print(f"Failed to pull camera data from session '{label}': {e}", flush=True)

    return {"error": str(e), "success": False}

@app.get("/robot/{label}")
async def get_robot(label: str):

  try:
    db: Database = app.state.db
    data = await db.retrieve_robot(label)

    return {"data": data, "success": True}
  except Exception as e:
    print(f"Failed to pull robot data from session '{label}': {e}", flush=True)

    return {"error": str(e), "success": False}


@app.get("/session/start/{label}")
async def start_session(label: str):
    try:
        db: Database = app.state.db
        await db.create_session(label=label)

        return {"message": f"Session started with label: {label}", "success": True}
    except Exception as e:
        print(f"Failed to start session '{label}': {e}", flush=True)

        return {"error": str(e), "success": False}

@app.get("/session/stop")
async def stop_session():

  try:

    db: Database = app.state.db
    await db.end_session()

    msg = try_backup()

    return {"message": f"Current Session Ended", "backup": msg, "success": True}
  except Exception as e:

    print(f"Failed to stop the current session: {e}", flush=True)

    return {"error": str(e), "success": False}

@app.on_event("startup")
async def startup():

  # Start up DB connection
  app.state.db = await Database.create()
  app.state.broadcast_robot_event = broadcast_robot_event
  # Start up TCP listener
  port = int(os.getenv("ROBOT_TCP_PORT", "5001"))
  app.state.tcp_server = await start_tcp_server(app, port=port)

@app.on_event("shutdown")
async def shutdown():
    srv = getattr(app.state, "tcp_server", None)

    if srv:
        srv.close()
        await srv.wait_closed()

@mqtt.subscribe("imu/#")
async def handle_sensors(client, topic, payload, qos, prop):
  device_label = topic.split("/")[1]
  msg = [part.strip() for part in payload.decode().split(",")]
  #msg = f"{datetime.utcnow().isoformat()} | {topic} | {payload.decode(errors='ignore')}"
  #print(msg, flush=True)

  try:
    db: Database = app.state.db
    
    await mqtt_event_queue.put(msg)

    await db.insert_imu_data(
      device_label=device_label,
      recorded_at = float(msg[0]), 
      accel_x = float(msg[1]), 
      accel_y = float(msg[2]), 
      accel_z = float(msg[3]), 
      gryo_x = float(msg[4]), 
      gryo_y = float(msg[5]), 
      gryo_z = float(msg[6]), 
      mag_x = float(msg[7]), 
      mag_y = float(msg[8]), 
      mag_z = float(msg[9]), 
      yaw = float(msg[10]), 
      pitch = float(msg[11]), 
      roll = float(msg[12])
    )
    print(f"Successful store")

  except Exception as e:
    print(f"DB insert failed for topic={topic}: {e}", flush=True)

@mqtt.subscribe("camera/#")
async def handle_camera(client, topic, payload, qos, prop):

  device_label = topic.split("/")[1]
  #msg = [part.strip() for part in payload.decode().split(",")]
  #msg = f"{datetime.utcnow().isoformat()} | {topic} | {payload.decode(errors='ignore')}"
  msg = [p.strip() for p in payload.decode().split(",")]

  #print(msg, flush=True)

  try:
    db: Database = app.state.db

    await mqtt_event_queue.put(msg)

    await db.insert_camera_data(
      device_label = device_label,
      recorded_at = float(msg[0]),
      frame_idx = int(msg[1]), 
      marker_idx = int(msg[2]), 
      rvec_x = float(msg[3]), 
      rvec_y = float(msg[4]), 
      rvec_z = float(msg[5]), 
      tvec_x = float(msg[6]), 
      tvec_y = float(msg[7]), 
      tvec_z = float(msg[8]), 
      image_path = msg[9]
    )

  except Exception as e:
    print(f"DB insert failed for topic={topic}: {e}", flush=True)

@mqtt.on_message()
async def message(client, topic, payload, qos, prop):
  msg = f"Message from device ({topic}): {payload.decode()}"

  print(msg)
