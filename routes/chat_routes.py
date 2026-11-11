
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from database import SessionLocal
from core.templates import templates
from service import auth_service, group_service, chat_service

import os
from dotenv import load_dotenv
import logging



router = APIRouter()


load_dotenv()

ALLOWED_WS_ORIGINS = {
    origin.strip().rstrip("/")
    for origin in os.getenv("ALLOWED_WS_ORIGINS", "").split(",")
    if origin.strip()
}

logger = logging.getLogger(__name__)

# =====================================
# WEBSOCKET : DISCUSSION EN TEMPS RÉEL
# =====================================

@router.websocket("/ws/{group_id}")
async def websocket_chat(
    websocket: WebSocket,
    group_id: int,
):

    # Vérifier l'origine de la connexion
    origin = websocket.headers.get("origin", "").rstrip("/")

    if origin not in ALLOWED_WS_ORIGINS:
        await websocket.close(code=1008)
        return
     # Vérifier la session de l'utilisateur
    user_id = websocket.scope.get(
        "session",
        {},
    ).get("user_id")

    if not user_id:
        await websocket.close(code=1008)
        return

    # Récupérer l'utilisateur et le groupe
    async with SessionLocal() as db:

        user = await auth_service.get_user_by_id(
            db,
            user_id,
        )

        group = await group_service.get_group(
            db,
            group_id,
        )

    if user is None or group is None:
        await websocket.close(code=1008)
        return

    # Vérifier que l'utilisateur est membre accepté
    async with SessionLocal() as db:
        is_member = await group_service.is_group_member(
            db,
            user_id,
            group_id,
        )

    if not is_member:
        await websocket.close(code=1008)
        return

    username = user.username

    # Connecter l'utilisateur au groupe
    await chat_service.manager.connect(
        websocket,
        group_id,
    )
    
    try:
        while True:

            try:
                packet = await websocket.receive()
                if packet["type"] == "websocket.disconnect":
                    break
                raw_data = packet.get("text")
                if raw_data is None:
                    continue

                if len(raw_data.encode("utf-8")) > 16_384:
                    await websocket.close(code=1009)
                    break

                data = json.loads(raw_data)
                
            except json.JSONDecodeError:
                continue
  
            if not isinstance(data, dict):
                continue

            raw_content = data.get("content", "")

            if not isinstance(raw_content, str):
                continue

            if len(raw_content) > 4000:
                continue

            content = raw_content.strip()

            if not content:
                continue

            

            if not chat_service.manager.can_send_message(user_id):
                continue

            
            # Enregistrer le message
            message = await chat_service.save_message(
                group_id,
                username,
                content,
            )

            # Générer le HTML du message
            html = templates.get_template(
                "message.html"
            ).render(
                message=message,
                current_username=username,
            )

            # Diffuser le message
            await chat_service.manager.broadcast(
                group_id,
                html,
            )

    except WebSocketDisconnect:
        pass

    except Exception:
        logger.exception(
            "Erreur inattendue dans le WebSocket du groupe %s",
            group_id
        )
        raise

    finally:
        chat_service.manager.disconnect(websocket, group_id)