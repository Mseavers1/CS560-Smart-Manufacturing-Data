from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
from ntp_facade_smr import TimeBrokerFacade
from typing import List
from zoneinfo import ZoneInfo
import json

# Created in junction using GPT
class ConnectionManager:

    def __init__(self):
        self.active: List[WebSocket] = []

    def get_time(self):
        try:
            # tbroker = TimeBrokerFacade(ntp_server_ip = '192.168.1.76')
        
            unix_time = datetime.now(timezone.utc).timestamp()

            dt = datetime.fromtimestamp(unix_time, tz=ZoneInfo("UTC"))

            return dt.astimezone(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d %I:%M:%S %p %Z")


        except(ValueError, IOError) as e:
            print(f"Error: {e}")

    async def connect(self, ws: WebSocket):

        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):

        if ws in self.active:
            self.active.remove(ws)

    async def broadcast_json(self, payload: dict):

        payload = payload.copy()
        payload["timestamp"] = self.get_time()

        msg = json.dumps(payload)
        for ws in self.active:
            try:
                await ws.send_text(msg)
            except Exception:
                self.disconnect(ws)

camera_manager = ConnectionManager()
imu_manager = ConnectionManager()
robot_manager = ConnectionManager()
misc_manager = ConnectionManager()

MANAGERS = {
    "camera": camera_manager,
    "imu": imu_manager,
    "robot": robot_manager,
    "misc": misc_manager
}