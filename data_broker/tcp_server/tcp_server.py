# app/tcp_server.py
import os
import asyncio
from typing import Optional, Tuple
from datetime import datetime
from app import loggers
from db.database import DatabaseSingleton
import aiohttp
import time

QUEUE_SIZE = 5000

robot_queue = asyncio.Queue(maxsize=QUEUE_SIZE)

async def send_to_fastapi(msg: str, msg_type: str = "normal"):

    url = "http://192.168.1.76:8000/send/robot"

    payload = {
        "type": msg_type,
        "text": msg
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    print(f"[ERROR] FastAPI broadcast failed ({resp.status}): {text}")
                else:
                    print(f"[OK] Sent broadcast to /send/robot")
    except Exception as e:
        print(f"[ERROR] Could not reach FastAPI API: {e}")

# Continuously comsumes the queue and performs batched DB insertions
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


# Handles TCP Connection
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
                        "ts": int(parts[1]),
                        "joint1": float(parts[2]),
                        "joint2": float(parts[3]),
                        "joint3": float(parts[4]),
                        "joint4": float(parts[5]),
                        "joint5": float(parts[6]),
                        "joint6": float(parts[7]),
                        "x": float(parts[8]),
                        "y": float(parts[9]),
                        "z": float(parts[10]),
                        "w": float(parts[11]),
                        "p": float(parts[12]),
                        "r": float(parts[13]),
                        "recorded_at": db.get_time()
                    }

                    await robot_queue.put(data)
                    loggers.cur_robot_logger.info(f"Queued message: {text}")
                except Exception as e:
                    loggers.cur_robot_logger.error(f"Parse error: {e}")

    except asyncio.CancelledError:
        loggers.cur_robot_logger.info("Robot handler cancelled")
    finally:
        writer.close()
        await writer.wait_closed()
        loggers.cur_robot_logger.info("Writer Closed")


async def start_tcp_server(host: Optional[str] = None, port: int = 5001):
    host = host or os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("ROBOT_TCP_PORT", port))

    server = await asyncio.start_server(handle_robot, host=host, port=port)
    sockets = ", ".join(str(s.getsockname()) for s in (server.sockets or []))
    loggers.cur_robot_logger.info(f"[TCP] Listening on {sockets}")

    asyncio.create_task(robot_worker(batch_size=50, flush_interval=1))

    async with server:
        await server.serve_forever()


def main():
    loggers.create_loggers()
    loggers.cur_robot_logger.info("Starting TCP server...")

    try:
        asyncio.run(start_tcp_server())
    except KeyboardInterrupt:
        loggers.cur_robot_logger.info("TCP server stopped by user.")
    except Exception as e:
        loggers.cur_robot_logger.error(f"TCP server crashed: {e}")
    finally:
        asyncio.run(DatabaseSingleton.close())


if __name__ == "__main__":
    main()
