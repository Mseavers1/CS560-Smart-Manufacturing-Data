import asyncio
from typing import Optional, Tuple

# Listener for messages from socket
async def handle_robot(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, app):
    peer: Optional[Tuple[str, int]] = writer.get_extra_info("peername")

    try:

        while True:
            line = await reader.readline()

            # Client closes
            if not line:
                break

            # Decode message
            text = line.decode("utf-8", errors="replace").strip()
            parts = [p.strip() for p in text.split(",")]

            print(f"TCP message received: {text}", flush=True)

            try:
                db: Database = app.state.db

                await db.insert_robot_data(
                ts_str = parts[0], 
                ts_int = int(parts[1]), 
                recorded_at = db.get_time(), 
                j1 = float(parts[2]), 
                j2 = float(parts[3]), 
                j3 = float(parts[4]), 
                j4 = float(parts[5]), 
                j5 = float(parts[6]), 
                j6 = float(parts[7]), 
                x = float(parts[8]), 
                y = float(parts[9]), 
                z = float(parts[10]), 
                w = float(parts[11]), 
                p = float(parts[12]), 
                r = float(parts[13]), 
                received_utc=float(parts[14])
                )

            except Exception as e:
                print(f"DB insert failed for topic=ROBOT/MAIN: {e}", flush=True)




    except Exception as e:
        print(f"TCP Connection error from {peer}: {e}", flush=True)

    finally:
        writer.close()
        await writer.wait_closed()

# Call to start tcp listener
async def start_tcp_server(app, host="0.0.0.0", port=5001):
    server = await asyncio.start_server(lambda r, w: handle_robot(r, w, app), host, port)
    sockets = ", ".join(str(s.getsockname()) for s in server.sockets or [])
    print(f"TCP Robot server listening on {sockets}", flush=True)
    return server
