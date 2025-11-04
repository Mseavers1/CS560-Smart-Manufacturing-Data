from fastapi import WebSocket, WebSocketDisconnect
from typing import List

# Created in junction using GPT
class ConnectionManager:

    def __init__(self) -> None:
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):

        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):

        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: str):
        dead = []

        for ws in self.active:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

camera_manager = ConnectionManager()
imu_manager = ConnectionManager()
robot_manager = ConnectionManager()