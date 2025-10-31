# app/tcp_server.py
import os
import asyncio
from typing import Optional, Tuple
from datetime import datetime

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

                # TODO: parse/insert to DB if desired
                # parts = [p.strip() for p in text.split(",")]
                # db: Database = app.state.db
                # await db.insert_robot_row(...)

                # (optional) echo to UI stream
                try:
                    await app.state.broadcast_robot_event(
                        f'{{"type":"row","text":"{text}","ts":"{datetime.utcnow().isoformat()}Z"}}'
                    )
                except Exception:
                    pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def start_tcp_server(app, host: Optional[str] = None, port: int = 5001):
    """
    Start a TCP server that listens for robot lines.
    Binds to 0.0.0.0 by default so it's reachable from the LAN.
    """
    host = host or os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("ROBOT_TCP_PORT", port))
    server = await asyncio.start_server(lambda r, w: handle_robot(app, r, w), host=host, port=port)
    sockets = ", ".join(str(s.getsockname()) for s in (server.sockets or []))
    print(f"[robot-tcp] Listening on {sockets}", flush=True)
    return server
