
from pathlib import Path
from uuid import uuid4
from io import BytesIO

from fastapi import (
    APIRouter,
    Request,
    UploadFile,
    File,
    Depends,
    HTTPException,
)
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from PIL import Image, UnidentifiedImageError

from database import get_db
from core.templates import templates
from dependencies.auth import get_current_user
from service import group_service, chat_service


router = APIRouter()


# =====================================
# ENVOYER UNE IMAGE
# =====================================

@router.post("/groups/{group_id}/images")
async def upload_group_image(
    request: Request,
    group_id: int,
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Vous devez être connecté.",
        )

    group = await group_service.get_group(db, group_id)

    if group is None:
        raise HTTPException(
            status_code=404,
            detail="Groupe introuvable.",
        )

    # Limite de 5 Mo
    max_size = 5 * 1024 * 1024

    contents = await image.read(max_size + 1)
    await image.close()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Le fichier image est vide.",
        )

    if len(contents) > max_size:
        raise HTTPException(
            status_code=413,
            detail="L'image ne doit pas dépasser 5 Mo.",
        )

    # Vérifier le véritable format de l'image
    try:
        with Image.open(BytesIO(contents)) as img:
            img.verify()
            image_format = img.format

    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
    ):
        raise HTTPException(
            status_code=400,
            detail="Le fichier envoyé n'est pas une image valide.",
        )

    extensions = {
        "JPEG": ".jpg",
        "PNG": ".png",
        "WEBP": ".webp",
    }

    if image_format not in extensions:
        raise HTTPException(
            status_code=400,
            detail="Formats acceptés : JPG, PNG et WEBP.",
        )

    # Enregistrer l'image
    filename = f"{uuid4().hex}{extensions[image_format]}"

    destination = Path("uploads/images") / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(contents)

    image_path = f"/uploads/images/{filename}"

    message = await chat_service.save_image_message(
        group_id,
        user.username,
        image_path,
    )

    html = templates.get_template(
        "message.html"
    ).render(
        message=message,
        current_username=user.username,
    )

    await chat_service.manager.broadcast(
        group_id,
        html,
    )

    return Response(status_code=204)


# =====================================
# ENVOYER UN MESSAGE VOCAL
# =====================================

@router.post("/groups/{group_id}/audios")
async def upload_group_audio(
    request: Request,
    group_id: int,
    audio: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Vous devez être connecté.",
        )

    group = await group_service.get_group(db, group_id)

    if group is None:
        raise HTTPException(
            status_code=404,
            detail="Groupe introuvable.",
        )

    # Formats audio acceptés
    extensions = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/mp4": ".mp4",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
    }

    content_type = (
        audio.content_type or ""
    ).split(";")[0].lower()

    if content_type not in extensions:
        await audio.close()

        raise HTTPException(
            status_code=400,
            detail="Format audio non accepté.",
        )

    # Limite de 10 Mo
    max_size = 10 * 1024 * 1024

    contents = await audio.read(max_size + 1)
    await audio.close()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Le fichier audio est vide.",
        )

    if len(contents) > max_size:
        raise HTTPException(
            status_code=413,
            detail="Le vocal ne doit pas dépasser 10 Mo.",
        )

    # Enregistrer le vocal
    filename = f"{uuid4().hex}{extensions[content_type]}"

    destination = Path("uploads/audios") / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(contents)

    audio_path = f"/uploads/audios/{filename}"

    message = await chat_service.save_audio_message(
        group_id,
        user.username,
        audio_path,
    )

    html = templates.get_template(
        "message.html"
    ).render(
        message=message,
        current_username=user.username,
    )

    await chat_service.manager.broadcast(
        group_id,
        html,
    )

    return Response(status_code=204)
