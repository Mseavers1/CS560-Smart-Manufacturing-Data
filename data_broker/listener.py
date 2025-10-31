# listener.py
import socket, csv, time, os, pathlib

# ===== Settings =====
HOST = '0.0.0.0'             # listen on all interfaces (use your PC/RPi IP if you prefer)
PORT = 5001
EXPECTED_COLS = 12           # J1..J6 + X,Y,Z,W,P,R
OUT_DIR = 'Logs'             # folder to drop CSV files into
# =====================

# Make output directory if missing
pathlib.Path(OUT_DIR).mkdir(parents=True, exist_ok=True)

# Make a unique, timestamped filename each run
stamp = time.strftime("%Y%m%d_%H%M%S")
csv_path = os.path.join(OUT_DIR, f'robot_position_data_{stamp}.csv')

print(f"Listening on {HOST or '0.0.0.0'}:{PORT} ...")
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    conn, addr = s.accept()
    print(f"Connected by {addr}")
    print(f"Writing to: {csv_path}")

    buffer = ""
    header_seen = False

    with conn, open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Always write header on a new file
        writer.writerow(["ts_epoch", "J1", "J2", "J3", "J4", "J5", "J6",
                         "X", "Y", "Z", "W", "P", "R"])

        while True:
            chunk = conn.recv(4096)
            if not chunk:
                print("Connection closed by peer.")
                break

            buffer += chunk.decode('utf-8', errors='replace')

            # Split CRLF/CR/NL lines robustly
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                text = line.rstrip("\r").strip()
                if not text:
                    continue

                # Skip the robot's own CSV header (first time only)
                if not header_seen and text.upper().startswith("J1,"):
                    header_seen = True
                    continue

                parts = [p.strip() for p in text.split(',')]
                if len(parts) == EXPECTED_COLS:
                    try:
                        nums = [float(p) for p in parts]
                        writer.writerow([time.time()] + nums)
                        print(nums)
                        continue
                    except ValueError:
                        pass  # fall through and store raw

                # Fallback: write the raw line with timestamp in first column
                writer.writerow([time.time(), text])
                print(text)