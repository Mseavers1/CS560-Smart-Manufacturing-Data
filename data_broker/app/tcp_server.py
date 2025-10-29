import asyncio
from typing import Optional, Tuple
from datetime import datetime
import json

# Listener for messages from socket
async def handle_robot(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, app):
    peer: Optional[Tuple[str, int]] = writer.get_extra_info("peername")

    # announce connection
    try:
        await app.state.broadcast_robot_event(json.dumps({
            "type": "connection_open",
            "peer": f"{peer[0]}:{peer[1]}" if peer else "unknown",
            "ts": datetime.utcnow().isoformat() + "Z"
        }))
    except Exception:
        pass

    try:
        while True:
            line = await reader.readline()
            if not line:
                break

            text = line.decode("utf-8", errors="replace").strip()
            parts = [p.strip() for p in text.split(",")]

            print(f"TCP message received: {text}", flush=True)

            # Insert to database
            try:
                db: Database = app.state.db
                await db.insert_robot_data(
                    ts_str = parts[0],
                    ts_int = int(parts[1]),
                    recorded_at = db.get_time(),
                    j1=float(parts[2]), j2=float(parts[3]), j3=float(parts[4]),
                    j4=float(parts[5]), j5=float(parts[6]), j6=float(parts[7]),
                    x=float(parts[8]), y=float(parts[9]), z=float(parts[10]),
                    w=float(parts[11]), p=float(parts[12]), r=float(parts[13]),
                )
            except Exception as e:
                print(f"DB insert failed for topic=ROBOT/MAIN: {e}", flush=True)

            # Frontend
            try:
                payload = {
                    "type": "robot_data",
                    "peer": f"{peer[0]}:{peer[1]}" if peer else "unknown",
                    "ts": datetime.utcnow().isoformat() + "Z",
                    "raw": text,
                    "joints": [float(parts[i]) for i in range(2, 8)],
                    "pose":   [float(parts[i]) for i in range(8, 13)],
                }
                await app.state.broadcast_robot_event(json.dumps(payload))
            except Exception as e:
                print(f"Broadcast error: {e}", flush=True)

    except Exception as e:
        print(f"TCP Connection error from {peer}: {e}", flush=True)

    finally:
        try:
            await app.state.broadcast_robot_event(json.dumps({
                "type": "connection_close",
                "peer": f"{peer[0]}:{peer[1]}" if peer else "unknown",
                "ts": datetime.utcnow().isoformat() + "Z"
            }))
        except Exception:
            pass
        writer.close()
        await writer.wait_closed()


# Call to start tcp listener
async def start_tcp_server(app, host="0.0.0.0", port=5001):
    server = await asyncio.start_server(lambda r, w: handle_robot(r, w, app), host, port)
    sockets = ", ".join(str(s.getsockname()) for s in server.sockets or [])
    print(f"TCP Robot server listening on {sockets}", flush=True)

    if not hasattr(app.state, "broadcast_robot_event"):
        async def _broadcast(msg: str):
            await broadcast_robot_event(msg)
        app.state.broadcast_robot_event = _broadcast

    return server
