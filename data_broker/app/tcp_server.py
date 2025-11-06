# app/tcp_server.py
import os
import asyncio
from typing import Optional, Tuple
from datetime import datetime
from . import loggers
from .connection_manager import camera_manager, imu_manager, robot_manager

async def handle_robot(app, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):

    try:
        # CRLF/CR/LF tolerant line reader
        buf = b""
        while True:
            chunk = await reader.read(4096)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf or b"\r" in buf:
                # normalize endings to \n
                buf = buf.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                line, sep, buf = buf.partition(b"\n")
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                print(f"[robot-tcp] {text}", flush=True)

                await robot_manager.broadcast_json({
                "type": "normal",
                "text": "Message Recieved"
                })

                # Parse and send to DB
                try:
                    parts = [p.strip() for p in text.split(",")]
                    db: Database = app.state.db
                    await db.insert_robot_data(int(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7]), float(parts[8]), float(parts[9]), float(parts[10]), float(parts[11]), float(parts[12]), float(parts[13]), db.get_time())

                    await robot_manager.broadcast_json({
                    "type": "normal",
                    "text": "Message Stored"
                    })
                    
                except Exception as e:
                    await robot_manager.broadcast_json({
                    "type": "error",
                    "text": f"Message failed to store: {e}"
                    })
    finally:
        try:
            writer.close()
            await writer.wait_closed()
            loggers.cur_robot_logger.info(f"Writer Closed")
        except Exception as e:
            loggers.cur_robot_logger.error(f"Error: {e}")

async def start_tcp_server(app, host: Optional[str] = None, port: int = 5001):
    host = host or os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("ROBOT_TCP_PORT", port))
    server = await asyncio.start_server(lambda r, w: handle_robot(app, r, w), host=host, port=port)
    sockets = ", ".join(str(s.getsockname()) for s in (server.sockets or []))
    print(f"[robot-tcp] Listening on {sockets}", flush=True)
    return server
