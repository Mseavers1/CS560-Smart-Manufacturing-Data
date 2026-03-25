import os
import asyncio
import aiohttp
import time
from typing import Optional
import paho.mqtt.client as mqtt
from pycomm3 import LogixDriver

from fast_server import loggers
from db.database import DatabaseSingleton

# -----------------------------
# CONFIG
# -----------------------------
PLC_IP = os.getenv("PLC_IP", "1.1.1.1")  # 10.5.60.27, currently dummy 
START_TAG = os.getenv("PLC_START_TAG", "Trigger_Wave")
FINISH_TAG = os.getenv("PLC_FINISH_TAG", "Robot_Finished")

MQTT_HOST = os.getenv("MQTT_HOST", os.getenv("HOST_IP", "localhost"))
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_COMMAND_TOPIC = os.getenv("ROBOT_COMMAND_TOPIC", "cmd/robot/start")

ROBOT_FINISH_TIMEOUT = float(os.getenv("ROBOT_FINISH_TIMEOUT", 120.0))

# Batched info for ROBOT
queue_size = int(os.getenv("QUEUE_SIZE", 5000))
robot_queue = asyncio.Queue(maxsize=queue_size)

# Prevent overlapping start commands
robot_start_lock = asyncio.Lock()


# -----------------------------
# FASTAPI MESSAGE HELPER
# -----------------------------
async def send_to_fastapi(msg: str, msg_type: str = "normal", channel: str = "robot"):
    host = os.getenv("FASTAPI_HOST", os.getenv("HOST_IP", "localhost"))
    port = os.getenv("FASTAPI_PORT", "8000")

    url = f"http://{host}:{port}/send/{channel}"

    payload = {
        "type": msg_type,
        "text": msg,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"FastAPI broadcast failed ({resp.status}): {text}")
    except Exception as e:
        print(f"Could not reach FastAPI API: {e}")

# -----------------------------
# PLC CONTROL
# -----------------------------
def run_plc_start_sequence_blocking() -> None:
    loggers.cur_robot_logger.info(f"[PLC] Connecting to PLC at {PLC_IP}")

    with LogixDriver(PLC_IP) as plc:
        loggers.cur_robot_logger.info(f"[PLC] Pulsing '{START_TAG}' HIGH for 0.5 seconds")
        plc.write(START_TAG, True)
        time.sleep(0.5)
        plc.write(START_TAG, False)

        loggers.cur_robot_logger.info(f"[PLC] Waiting for '{FINISH_TAG}' feedback")
        start_wait = time.monotonic()

        while True:
            response = plc.read(FINISH_TAG)

            if response.value is True:
                loggers.cur_robot_logger.info(f"[PLC] {FINISH_TAG} detected. Robot cycle complete")
                return

            if (time.monotonic() - start_wait) >= ROBOT_FINISH_TIMEOUT:
                raise TimeoutError(
                    f"Timed out after {ROBOT_FINISH_TIMEOUT:.1f}s waiting for PLC tag '{FINISH_TAG}'"
                )

            time.sleep(0.1)


async def run_robot_start_sequence():
    if robot_start_lock.locked():
        loggers.cur_robot_logger.warning("[TCP Server] Robot start command received while a start is already in progress")
        await send_to_fastapi("[TCP Server] Robot start already in progress", "error", "misc")
        return

    async with robot_start_lock:
        loggers.cur_robot_logger.info("[TCP Server] Robot start command received")
        await send_to_fastapi("[TCP Server] Robot start command received", "info", "misc")

        try:
            loggers.cur_robot_logger.info("[TCP Server] Starting PLC handshake sequence")
            await send_to_fastapi("[TCP Server] Starting PLC handshake sequence", "info", "misc")

            await asyncio.to_thread(run_plc_start_sequence_blocking)

            loggers.cur_robot_logger.info("[TCP Server] Robot start sequence completed successfully")
            await send_to_fastapi("[TCP Server] Robot start sequence completed successfully", "info", "misc")
        except Exception as e:
            loggers.cur_robot_logger.error(f"[TCP Server] Robot start sequence failed: {e}")
            await send_to_fastapi(f"[TCP Server] Robot start sequence failed: {e}", "error", "misc")

# -----------------------------
# MQTT COMMAND SUBSCRIBER
# -----------------------------
def create_mqtt_client(event_loop: asyncio.AbstractEventLoop) -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            loggers.cur_robot_logger.info(f"[MQTT] Connected to broker at {MQTT_HOST}:{MQTT_PORT}")
            client.subscribe(MQTT_COMMAND_TOPIC)
            loggers.cur_robot_logger.info(f"[MQTT] Subscribed to topic '{MQTT_COMMAND_TOPIC}'")
        else:
            loggers.cur_robot_logger.error(f"[MQTT] Failed to connect to broker, rc={rc}")

    def on_message(client, userdata, message):
        try:
            payload = message.payload.decode("utf-8", errors="replace").strip()
            topic = str(message.topic)

            loggers.cur_robot_logger.info(f"[MQTT] Received command on '{topic}': {payload}")

            if topic == MQTT_COMMAND_TOPIC:
                asyncio.run_coroutine_threadsafe(run_robot_start_sequence(), event_loop)
        except Exception as e:
            loggers.cur_robot_logger.error(f"[MQTT] Error handling command message: {e}")

    client.on_connect = on_connect
    client.on_message = on_message

    return client


# -----------------------------
# ROBOT DB WORKER
# -----------------------------
async def robot_worker(batch_size=50, flush_interval=2.0):
    db = await DatabaseSingleton.get_instance()
    batch = []
    last_flush = time.monotonic()

    while True:
        try:
            item = await asyncio.wait_for(robot_queue.get(), timeout=0.5)
            batch.append(item)
        except asyncio.TimeoutError:
            pass

        now = time.monotonic()
        if (len(batch) >= batch_size) or (batch and (now - last_flush) >= flush_interval):
            try:
                await db.insert_robot_batch(batch)
                loggers.cur_robot_logger.info(f"Inserted {len(batch)} robot rows.")
                await send_to_fastapi(f"Inserted {len(batch)} robot rows.")
                batch.clear()
                last_flush = now
            except Exception as e:
                loggers.cur_robot_logger.error(f"DB batch insert failed: {e}")
                await send_to_fastapi(f"Failed to store message: {e}", "error")
                await asyncio.sleep(1)

        await asyncio.sleep(0)


# -----------------------------
# TCP ROBOT INGESTION
# -----------------------------
async def handle_robot(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    db = await DatabaseSingleton.get_instance()
    buf = b""

    try:
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                break

            buf += chunk.replace(b"\r\n", b"\n").replace(b"\r", b"\n")

            while b"\n" in buf:
                line, _, buf = buf.partition(b"\n")
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue

                try:
                    parts = [p.strip() for p in text.split(",")]

                    data = {
                        "frame_id": int(parts[0]),
                        "ts": float(parts[1]),
                        "ts_string": parts[2],
                        "joint1": float(parts[3]),
                        "joint2": float(parts[4]),
                        "joint3": float(parts[5]),
                        "joint4": float(parts[6]),
                        "joint5": float(parts[7]),
                        "joint6": float(parts[8]),
                        "x": float(parts[9]),
                        "y": float(parts[10]),
                        "z": float(parts[11]),
                        "w": float(parts[12]),
                        "p": float(parts[13]),
                        "r": float(parts[14]),
                        "recorded_at": db.get_time(),
                    }

                    await robot_queue.put(data)
                    loggers.cur_robot_logger.info(f"Queued message: {text}")
                except Exception as e:
                    print(f"ROBOT PARSE ERROR: {e} line={text!r}")
                    loggers.cur_robot_logger.error(f"Parse error: {e}")

    except asyncio.CancelledError:
        loggers.cur_robot_logger.info("Robot handler cancelled")
    finally:
        writer.close()
        await writer.wait_closed()
        loggers.cur_robot_logger.info("Writer Closed")


# -----------------------------
# SERVER STARTUP
# -----------------------------
async def start_tcp_server(host: Optional[str] = None, port: int = 5001):
    host = host or os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("ROBOT_TCP_PORT", port))
    batch_size = int(os.getenv("BATCHES", 50))
    batch_timeout = float(os.getenv("B_TIMEOUT", 1.0))

    loop = asyncio.get_running_loop()

    mqtt_client = create_mqtt_client(loop)
    mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()

    server = await asyncio.start_server(handle_robot, host=host, port=port)
    sockets = ", ".join(str(s.getsockname()) for s in (server.sockets or []))
    loggers.cur_robot_logger.info(f"[TCP] Listening on {sockets}")

    asyncio.create_task(robot_worker(batch_size=batch_size, flush_interval=batch_timeout))

    try:
        async with server:
            await server.serve_forever()
    finally:
        loggers.cur_robot_logger.info("[MQTT] Stopping MQTT client")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


def main():
    loggers.create_loggers()
    loggers.cur_robot_logger.info("Starting TCP fast_server with MQTT command subscriber...")

    try:
        asyncio.run(start_tcp_server())
    except KeyboardInterrupt:
        loggers.cur_robot_logger.info("TCP fast_server stopped by user.")
    except Exception as e:
        loggers.cur_robot_logger.error(f"TCP fast_server crashed: {e}")
    finally:
        asyncio.run(DatabaseSingleton.close())


if __name__ == "__main__":
    main()