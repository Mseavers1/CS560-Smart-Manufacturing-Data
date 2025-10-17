# conda activate data 
# uvicorn main:app --host 0.0.0.0 --port 8000 --reload   --- Server
# mosquitto_sub -h localhost -t "test/topic" -v          --- Broker Listening Test (Don't need with code below)
#    --- Client sends message (Sends the message or info) [test only] -- Devices need code that is shown in client.py

# sudo systemctl start mosquitto -- Do status to see if it is running but if not, start it
# make sure moquitto is not running before building ^^^
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi_mqtt import FastMQTT, MQTTConfig
import os
from .database import Database
from typing import List

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

@app.get("/session/start")
def start_session():

  try:
    db: Database = app.state.db

    await db.create_session (label=device_id)

  except Exception as e:
    print(f"DB insert failed for topic={topic}: {e}", flush=True)

@app.get("/session/stop")
def stop_session():
  pass

@app.on_event("startup")
async def startup():
    app.state.db = await Database.create()

@mqtt.subscribe("robot/#")
async def handle_sensors(client, topic, payload, qos, prop):
  msg = f"Sensor ({topic}): {payload.decode()}"
  print(msg)

@mqtt.subscribe("sensor/#")
async def handle_sensors(client, topic, payload, qos, prop):
  msg = f"Sensor ({topic}): {payload.decode()}"
  print(msg)

@mqtt.subscribe("camera/#")
async def handle_camera(client, topic, payload, qos, prop):

  device_id = topic.split("/")[1]
  msg = payload.decode()

  print(msg, flush=True)

  try:
    db: Database = app.state.db

    await db.insert_device(
        label=device_id,
        category="camera",
        ip_address="0.0.0.0",
        )

  except Exception as e:
    print(f"DB insert failed for topic={topic}: {e}", flush=True)

@mqtt.on_message()
async def message(client, topic, payload, qos, prop):
  msg = f"Message from device ({topic}): {payload.decode()}"
  print(msg)