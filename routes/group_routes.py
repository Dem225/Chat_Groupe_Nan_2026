
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from core.templates import templates
from dependencies.auth import get_current_user
from service import group_service


router = APIRouter()


# =====================================
# PAGE D'ACCUEIL : LISTE DES GROUPES
# =====================================

@router.get("/", response_class=HTMLResponse)
async def accueil(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    if user is None:
        return RedirectResponse("/connexion", status_code=303)

    groups = await group_service.get_groups(db)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "groups": groups,
            "user": user,
        },
    )


# =====================================
# CRÉER UN GROUPE
# =====================================

@router.post("/groups")
async def create_group(
    request: Request,
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    if user is None:
        return RedirectResponse("/connexion", status_code=303)

    try:
        await group_service.create_group(db, name)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return RedirectResponse("/", status_code=303)


# =====================================
# AFFICHER UN GROUPE
# =====================================

@router.get("/groups/{group_id}/view", response_class=HTMLResponse)
async def group_view(
    request: Request,
    group_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    if user is None:
        return RedirectResponse("/connexion", status_code=303)

    group = await group_service.get_group(db, group_id)

    if group is None:
        raise HTTPException(
            status_code=404,
            detail="Groupe introuvable.",
        )

    messages = await group_service.get_group_messages(
        db,
        group_id,
    )

    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={
            "group": group,
            "messages": messages,
            "user": user,
        },
    )
