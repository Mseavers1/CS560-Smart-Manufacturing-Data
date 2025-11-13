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

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi_mqtt import FastMQTT, MQTTConfig
import os
from db.database import DatabaseSingleton
from typing import List, AsyncGenerator, Dict, Any, Optional, Set
# from .tcp_server import handle_robot, start_tcp_server
from pathlib import Path
import subprocess
from fastapi.middleware.cors import CORSMiddleware
from collections import deque
import logging
from . import loggers
from app.connection_manager import camera_manager, imu_manager, robot_manager, misc_manager, MANAGERS


mqtt_config = MQTTConfig(
    host="host.docker.internal",
    port=1883,
    keepalive=60,
)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://192.168.1.76",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://192.168.1.76:5173",
        "http://192.168.1.76:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


mqtt = FastMQTT(config=mqtt_config)
mqtt.init_app(app)

web_camera_messages = []
web_imu_messages = []
web_robot_messages = []
web_global_errors = []

async def try_backup():

    await misc_manager.broadcast_json({
        "type": "normal",
        "text": "DB Backup Started"
    })

    try:
        db: Database = app.state.db
        backup_path = db.create_backup()

        return {
            "success": True,
            "path": backup_path
        }

        await misc_manager.broadcast_json({
            "type": "normal",
            "text": "DB Backup Finished"
        })

    except Exception as e:

        await misc_manager.broadcast_json({
            "type": "error",
            "text": f"Failed to backup DB: {e}"
        })

        loggers.log_system_logger(f"Failed to backup DB: {e}", True)

        return {
            "success": False,
            "error": str(e)
        }


@app.websocket("/ws/camera")
async def camera_ws(websocket: WebSocket):
    await camera_manager.connect(websocket)
    # print("Client connected. Active:", len(camera_manager.active))
    # loggers.log_system_logger(f"Camera WB connected. There is now a total of {camera_manager.active} connections.")

    try:
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        # print("WebSocket error:", e)
        loggers.log_system_logger(f"Camera WB Error: {e}", True)
    finally:
        camera_manager.disconnect(websocket)
        # print("Client disconnected. Active:", len(camera_manager.active))
        # loggers.log_system_logger(f"Camera WB disconnected. There is now a total of {camera_manager.active} connections.")


@app.websocket("/ws/robot")
async def robot_ws(websocket: WebSocket):
    await robot_manager.connect(websocket)
    #print("Client connected. Active:", len(robot_manager.active))
    # loggers.log_system_logger(f"Robot WB connected with a total of {robot_manager.active} connections.")
    
    try:
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        #print("WebSocket error:", e)
        loggers.log_system_logger(f"Robot WB Error: {e}", True)
    
    finally:
        robot_manager.disconnect(websocket)
        #print("Client disconnected. Active:", len(robot_manager.active))
        # loggers.log_system_logger(f"Robot WB connected with a total of {robot_manager.active} connections.")

@app.websocket("/ws/imu")
async def imu_ws(websocket: WebSocket):
    await imu_manager.connect(websocket)
    #print("Client connected. Active:", len(imu_manager.active))
    # loggers.log_system_logger(f"IMU WB connected with a total of {imu_manager.active} connections.")
    
    try:
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        # print("WebSocket error:", e)
        loggers.log_system_logger(f"IMU WB Error: {e}", True)
    finally:
        imu_manager.disconnect(websocket)
        #print("Client disconnected. Active:", len(imu_manager.active))
        # loggers.log_system_logger(f"IMU WB connected with a total of {imu_manager.active} connections.")

@app.websocket("/ws/misc")
async def misc_ws(websocket: WebSocket):
    await misc_manager.connect(websocket)
    # print("Client connected. Active:", len(misc_manager.active))
    # loggers.log_system_logger(f"Misc WB connected with a total of {misc_manager.active} connections.")

    try:
        while True:
            await asyncio.sleep(3600)
    except Exception as e:
        # print("WebSocket error:", e)
        loggers.log_system_logger(f"Misc WB Error: {e}", True)
    finally:
        misc_manager.disconnect(websocket)
        # print("Client disconnected. Active:", len(misc_manager.active))
        # loggers.log_system_logger(f"Misc WB connected with a total of {misc_manager.active} connections.")

@app.post("/send/{channel}")
async def send_channel(channel: str, payload: dict):

    mgr = MANAGERS.get(channel)

    if not mgr:
        raise HTTPException(404, "unknown channel")

    # Expected Messages: {"type":"normal|info|error", "text":"..."}
    if "text" not in payload:
        raise HTTPException(400, "missing 'text'")

    if "type" not in payload:
        payload["type"] = "normal"

    await mgr.broadcast_json(payload)
    return {"success": True}


@app.get("/backup/list")
def list_backups():

  folder = Path("/db_backups")
  files = []

  # List all files
  for file in folder.iterdir():
    if file.is_file():
      files.append(file.name)

  return {"files": files}

# Manually backup
@app.get("/backup")
async def backup():
  return await try_backup()

@app.post("/backup/restore/{filename}")
async def restore_backup(filename: str):
    try:

        db: Database = app.state.db
        path = f"/db_backups/{filename}"

        # Restore the DB
        await db.restore_backup(path)

        await misc_manager.broadcast_json({
            "type": "info",
            "text": f"Restored backup: {filename}"
        })

        return {"success": True}

    except Exception as e:
        await misc_manager.broadcast_json({
            "type": "error",
            "text": f"Restore failed: {e}"
        })

        loggers.log_system_logger(f"Failed to restore backup: {e}", True)

        return {"success": False, "error": str(e)}

        raise HTTPException(500, detail=str(e))

# Test ping if server is running and recieving
# @app.get("/ping")
# def ping():
#   return {"status": "ok"}

@app.get("/imu/latest")
async def get_sessions():
  try:
    db: Database = app.state.db
    data = await db.get_latest_imu()

    return {"data": data, "success": True}
  except Exception as e:
    # print(f"Failed to pull latest imu: {e}", flush=True)
    loggers.log_system_logger(f"Failed to pull latest IMU: {e}", True)

    return {"error": str(e), "success": False}


@app.get("/camera/latest")
async def get_sessions():
  try:
    db: Database = app.state.db
    data = await db.get_latest_camera()

    return {"data": data, "success": True}
  except Exception as e:
    loggers.log_system_logger(f"Failed to pull latest CAMERA: {e}", True)

    return {"error": str(e), "success": False}


@app.get("/robot/latest")
async def get_sessions():
  try:
    db: Database = app.state.db
    data = await db.get_latest_robot()

    return {"data": data, "success": True}
  except Exception as e:
    loggers.log_system_logger(f"Failed to pull latest ROBOT: {e}", True)

    return {"error": str(e), "success": False}


@app.get("/sessions")
async def get_sessions():
  try:
    db: Database = app.state.db
    data = await db.retrieve_sessions()

    return {"data": data, "success": True}
  except Exception as e:
    loggers.log_system_logger(f"Failed to pull sessions: {e}", True)

    return {"error": str(e), "success": False}

@app.get("/session")
async def get_running_session():
    
    try:
        db: Database = app.state.db
        sess_id = db.current_session_id

        return {"id": sess_id if sess_id != None else -404, "data": sess_id != None, "success": True}

    except Exception as e:
        loggers.log_system_logger(f"Failed to get current session: {e}", True)

        return {"error": str(e), "success": False}


@app.get("/imu/{label}")
async def get_imu(label: str):

  try:
    db: Database = app.state.db
    data = await db.retrieve_imu(label)

    return {"data": data, "success": True}
  except Exception as e:
    loggers.log_system_logger(f"Failed to pull IMU data from session '{label}': {e}", True)

    return {"error": str(e), "success": False}

@app.get("/camera/{label}")
async def get_camera(label: str):

  try:
    db: Database = app.state.db
    data = await db.retrieve_camera(label)

    return {"data": data, "success": True}
  except Exception as e:
    loggers.log_system_logger(f"Failed to pull CAMERA data from session '{label}': {e}", True)

    return {"error": str(e), "success": False}

@app.get("/robot/{label}")
async def get_robot(label: str):

  try:
    db: Database = app.state.db
    data = await db.retrieve_robot(label)

    return {"data": data, "success": True}
  except Exception as e:
    loggers.log_system_logger(f"Failed to pull ROBOT data from session '{label}': {e}", True)

    return {"error": str(e), "success": False}


@app.get("/session/start/{label}")
async def start_session(label: str):

    loggers.create_loggers()

    try:
        db: Database = app.state.db
        await db.create_session(label=label)

        loggers.cur_camera_logger.info(f"Camera session ready with label: {label}")
        loggers.cur_imu_logger.info(f"IMU session ready with label: {label}")
        loggers.cur_robot_logger.info(f"Robot session ready with label: {label}")

        return {"message": f"Session started with label: {label}", "success": True}
    except Exception as e:
        loggers.log_system_logger(f"Failed to start session '{label}': {e}", True)

        loggers.cur_camera_logger.error(f"Camera session failed to start with label: {label}. Error: {e}")
        loggers.cur_imu_logger.error(f"IMU session failed to start with label: {label}. Error: {e}")
        loggers.cur_robot_logger.error(f"Robot session failed to start with label: {label}. Error: {e}")

        return {"error": str(e), "success": False}

@app.get("/session/stop")
async def stop_session():

  try:

    db: Database = app.state.db
    await db.end_session()

    loggers.cur_camera_logger.info(f"Camera session ended.")
    loggers.cur_imu_logger.info(f"IMU session ended.")
    loggers.cur_robot_logger.info(f"Robot session ended.")

    msg = await try_backup()

    return {"message": f"Current Session Ended", "backup": msg, "success": True}
  except Exception as e:

    loggers.log_system_logger(f"Failed to stop the current session: {e}", True)

    loggers.cur_camera_logger.error(f"Camera session failed to stop. Error: {e}")
    loggers.cur_imu_logger.error(f"IMU session failed to stop. Error: {e}")
    loggers.cur_robot_logger.error(f"Robot session failed to stop. Error: {e}")

    return {"error": str(e), "success": False}

@app.on_event("startup")
async def startup():
    app.state.db = await DatabaseSingleton.get_instance()

@app.on_event("shutdown")
async def shutdown_event():
    await DatabaseSingleton.close()

@mqtt.subscribe("imu/#")
async def handle_sensors(client, topic, payload, qos, prop):
  device_label = topic.split("/")[1]

  if device_label == "minipc2":
    return

  msg = [part.strip() for part in payload.decode().split(",")]
  #msg = f"{datetime.utcnow().isoformat()} | {topic} | {payload.decode(errors='ignore')}"
  #print(msg, flush=True)


  await imu_manager.broadcast_json({
        "type": "normal",
        "text": f"Message Recieved"
  })

  try:
    db: Database = app.state.db
    loggers.cur_imu_logger.info(f"IMU {device_label} recieved msg: {msg}")

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

    await imu_manager.broadcast_json({
        "type": "normal",
        "text": f"Message Stored"
    })

  except Exception as e:
    loggers.log_system_logger(f"DB insert failed for topic={topic}: {e}", True)


    loggers.cur_imu_logger.error(f"IMU failed to recieve with error: {e}")

    await imu_manager.broadcast_json({
        "type": "error",
        "text": f"Message failed to Store: {e}"
    })

@mqtt.subscribe("camera/#")
async def handle_camera(client, topic, payload, qos, prop):

  device_label = topic.split("/")[1]

  if device_label == "minipc2":
    return


  #msg = [part.strip() for part in payload.decode().split(",")]
  #msg = f"{datetime.utcnow().isoformat()} | {topic} | {payload.decode(errors='ignore')}"
  msg = [p.strip() for p in payload.decode().split(",")]

  #print(msg, flush=True)

  await camera_manager.broadcast_json({
        "type": "normal",
        "text": f"Message Recieved"
  })

  try:
    db: Database = app.state.db
    loggers.cur_camera_logger.info(f"Camera {device_label} recieved msg: {msg}")

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
      image_path = ""
    )

    await camera_manager.broadcast_json({
        "type": "normal",
        "text": f"Message Stored"
    })

  except Exception as e:
    loggers.log_system_logger(f"DB insert failed for topic={topic}: {e}", True)
    

    loggers.cur_camera_logger.error(f"IMU failed to recieve with error: {e}")
    await camera_manager.broadcast_json({
        "type": "error",
        "text": f"Failed to store: {e}"
    })