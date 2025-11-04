# app/tcp_server.py
import os
import asyncio
from typing import Optional, Tuple
from datetime import datetime
from . import loggers

async def handle_robot(app, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer: Optional[Tuple[str, int]] = writer.get_extra_info("peername")
    try:
        # announce to UI
        await app.state.broadcast_robot_event(
            f'{{"type":"robot_connected","peer":"{peer[0]}:{peer[1] if peer else 0}","ts":"{datetime.utcnow().isoformat()}Z"}}'
        )
    except Exception:
        pass

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

                # Parse and send to DB
                parts = [p.strip() for p in text.split(",")]
                db: Database = app.state.db
                await db.insert_robot_row(parts[1], parts[2], parts[3], parts[4], parts[5], parts[6], parts[7], parts[8], parts[9], parts[10], parts[11], parts[12], parts[13], db.get_time())

                try:
                    await app.state.broadcast_robot_event(
                        f'{{"type":"row","text":"{text}","ts":"{datetime.utcnow().isoformat()}Z"}}'
                    )

                    loggers.cur_robot_logger.info(f"Message recieved: {text}")
                except Exception as e:
                    loggers.cur_robot_logger.error(f"Error: {e}")
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
