
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from database import SessionLocal
from core.templates import templates
from service import auth_service, group_service, chat_service


router = APIRouter()


# =====================================
# WEBSOCKET : DISCUSSION EN TEMPS RÉEL
# =====================================

@router.websocket("/ws/{group_id}")
async def websocket_chat(
    websocket: WebSocket,
    group_id: int,
):
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
                data = json.loads(
                    await websocket.receive_text()
                )

            except json.JSONDecodeError:
                continue

            content = str(
                data.get("content", "")
            ).strip()[:4000]

            if not content:
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

    finally:
        chat_service.manager.disconnect(
            websocket,
            group_id,
        )
