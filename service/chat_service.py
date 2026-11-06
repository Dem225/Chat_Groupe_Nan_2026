from fastapi import WebSocket
from database import SessionLocal
from models import Message


class ConnectionManager:

    def __init__(self):
        self.connections = {}

    async def connect(self, websocket: WebSocket, group_id: int):
        await websocket.accept()

        self.connections.setdefault(group_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, group_id: int):
        if websocket in self.connections.get(group_id, []):
            self.connections[group_id].remove(websocket)

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