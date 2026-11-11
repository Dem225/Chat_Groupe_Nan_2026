from fastapi import WebSocket
from database import SessionLocal
from models import Message
import time

class ConnectionManager:

    def __init__(self):
        self.connections = {}
        self.last_message_times = {}

    def can_send_message(self, user_id: int) -> bool:
        current_time = time.monotonic()

        last_time = self.last_message_times.get(user_id, 0)

        if current_time - last_time < 1:
            return False

        self.last_message_times[user_id] = current_time

        return True

        
    async def connect(self, websocket: WebSocket, group_id: int):
        await websocket.accept()

        self.connections.setdefault(group_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, group_id: int):
        if websocket in self.connections.get(group_id, []):
            self.connections[group_id].remove(websocket)
        if not self.connections.get(group_id):
            self.connections.pop(group_id, None)
            
    async def broadcast(self, group_id: int, message: str):
        for connection in self.connections.get(group_id, [])[:]:
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection, group_id)


manager = ConnectionManager()


async def save_message(group_id: int, username: str, content: str):
    async with SessionLocal() as db:
        message = Message(
            username=username,
            content=content,
            group_id=group_id
        )

        db.add(message)
        await db.commit()
        await db.refresh(message)

        return {
            "username": message.username,
            "content": message.content,
            "created_at": message.created_at.strftime("%d/%m/%Y %H:%M"),
            "image_path": message.image_path,
            "audio_path": message.audio_path
        }



async def save_image_message(
    group_id: int,
    username: str,
    image_path: str,
):
    async with SessionLocal() as db:
        message = Message(
            username=username,
            content="",
            group_id=group_id,
            image_path=image_path,
        )

        db.add(message)
        await db.commit()
        await db.refresh(message)

        return {
            "username": message.username,
            "content": message.content,
            "image_path": message.image_path,
            "created_at": message.created_at.strftime(
                "%d/%m/%Y %H:%M"
            ),
        }


async def save_audio_message(
    group_id: int,
    username: str,
    audio_path: str,
):
    async with SessionLocal() as db:

        message = Message(
            username=username,
            content="",
            group_id=group_id,
            audio_path=audio_path,
        )

        db.add(message)
        await db.commit()
        await db.refresh(message)

        return {
            "username": message.username,
            "content": message.content,
            "image_path": message.image_path,
            "audio_path": message.audio_path,
            "created_at": message.created_at.strftime("%d/%m/%Y %H:%M"),
        }