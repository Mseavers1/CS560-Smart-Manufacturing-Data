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
from typing import List

# mqtt_config = MQTTConfig(
#     host=os.getenv("MQTT_HOST", "localhost"),
#     port=int(os.getenv("MQTT_PORT", 1883)),
#     keepalive=60,
# )

mqtt_config = MQTTConfig(
    host="host.docker.internal",
    port=1883,
    keepalive=60,
)

app = FastAPI()
mqtt = FastMQTT(config=mqtt_config)
mqtt.init_app(app)

messages: List[str] = []

# Test ping if server is running and recieving
@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
def index():
    # Simple HTML page with JS to fetch messages and display
    return """
    <!DOCTYPE html>
    <html>
    <head><title>MQTT Messages</title></head>
    <body>
      <h1>MQTT Messages</h1>
      <ul id="messages"></ul>

      <script>
        async function fetchMessages() {
          const res = await fetch('/messages');
          const data = await res.json();
          const ul = document.getElementById('messages');
          ul.innerHTML = '';
          data.forEach(msg => {
            const li = document.createElement('li');
            li.textContent = msg;
            ul.appendChild(li);
          });
        }

        // Fetch messages every 2 seconds
        setInterval(fetchMessages, 2000);
        fetchMessages();
      </script>
    </body>
    </html>
    """

@app.get("/messages")
def get_messages():
    # Return the list of messages as JSON
    return messages


@mqtt.subscribe("sensor/#")
async def handle_sensors(client, topic, payload, qos, prop):
    msg = f"Sensor ({topic}): {payload.decode()}"
    print(msg)
    messages.append(msg)

@mqtt.subscribe("camera/#")
async def handle_camera(client, topic, payload, qos, prop):
    msg = f"Camera ({topic}): {payload.decode()} [{client}]"
    print(msg)
    messages.append(msg)

@mqtt.on_message()
async def message(client, topic, payload, qos, prop):
    msg = f"Message from device ({topic}): {payload.decode()}"
    print(msg)
    messages.append(msg)