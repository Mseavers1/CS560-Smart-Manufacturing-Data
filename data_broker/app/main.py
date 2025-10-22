# conda activate data 
# uvicorn main:app --host 0.0.0.0 --port 8000 --reload   --- Server
# mosquitto_sub -h localhost -t "test/topic" -v          --- Broker Listening Test (Don't need with code below)
#    --- Client sends message (Sends the message or info) [test only] -- Devices need code that is shown in client.py

# sudo systemctl start mosquitto -- Do status to see if it is running but if not, start it
# make sure moquitto is not running before building ^^^


# To access db: docker exec -it postgres-db psql -U db_user -d manufacturing_db
# To backup db: docker exec -t postgres-db pg_dump -U db_user -d manufacturing_db > manufacturing_db.sql
# To recover db: cat manufacturing_db.sql | docker exec -i postgres-db psql -U db_user -d manufacturing_db


from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi_mqtt import FastMQTT, MQTTConfig
import os
from .database import Database
from typing import List
from .tcp_server import handle_robot, start_tcp_server

mqtt_config = MQTTConfig(
    host="host.docker.internal",
    port=1883,
    keepalive=60,
)

app = FastAPI()
mqtt = FastMQTT(config=mqtt_config)
mqtt.init_app(app)

# Test ping if server is running and recieving
@app.get("/ping")
def ping():
  return {"status": "ok"}

@app.get("/session/start/{label}")
async def start_session(label: str):
    try:
        db: Database = app.state.db
        await db.create_session(label=label)

        return {"message": f"Session started with label: {label}"}
    except Exception as e:
        print(f"Failed to start session '{label}': {e}", flush=True)

        return {"error": str(e)}

@app.get("/session/stop")
async def stop_session():

  try:

    db: Database = app.state.db
    await db.end_session()

    return {"message": f"Current Session Ended"}
  except Exception as e:

    print(f"Failed to stop the current session: {e}", flush=True)

    return {"error": str(e)}

@app.on_event("startup")
async def startup():

  # Start up DB connection
  app.state.db = await Database.create()
  
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

  print(msg, flush=True)

  try:
    db: Database = app.state.db

    await db.insert_imu_data(
      device_label=device_label,
      dev_id = msg[0],
      recorded_at = float(msg[1]), 
      other_time = msg[2], 
      accel_x = float(msg[3]), 
      accel_y = float(msg[4]), 
      accel_z = float(msg[5]), 
      gryo_x = float(msg[6]), 
      gryo_y = float(msg[7]), 
      gryo_z = float(msg[8]), 
      mag_x = float(msg[9]), 
      mag_y = float(msg[10]), 
      mag_z = float(msg[11]), 
      yaw = float(msg[12]), 
      pitch = float(msg[13]), 
      roll = float(msg[14])
    )

  except Exception as e:
    print(f"DB insert failed for topic={topic}: {e}", flush=True)

@mqtt.subscribe("camera/#")
async def handle_camera(client, topic, payload, qos, prop):

  device_label = topic.split("/")[1]
  msg = [part.strip() for part in payload.decode().split(",")]


  print(msg, flush=True)

  try:
    db: Database = app.state.db

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