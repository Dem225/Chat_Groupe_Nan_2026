
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from core.templates import templates
from dependencies.auth import get_current_user
from service import group_service
from dependencies.auth import get_optional_user, get_current_user
router = APIRouter()


# =====================================
# PAGE D'ACCUEIL : LISTE DES GROUPES
# =====================================

@router.get("/", response_class=HTMLResponse)
async def accueil(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_optional_user(request, db)

    if user is None:
        return RedirectResponse("/connexion", status_code=303)

    groups = await group_service.get_groups(db, user.id)
    invitations = await group_service.get_pending_invitations(
    db,
    user.id)
    flash_message = request.session.pop("flash_message", None)
    flash_type = request.session.pop("flash_type", None)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "groups": groups,
            "invitations": invitations,
            "user": user,
            "flash_message": flash_message,
            "flash_type": flash_type,
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
        await group_service.create_group(db, name, user.id)

    except ValueError as error:
        request.session["flash_message"] = str(error)
        request.session["flash_type"] = "error"

        return RedirectResponse(
            "/",
            status_code=303,
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

    is_member = await group_service.is_group_member(
    db,
    user.id,
    group_id
    )

    if not is_member:
        raise HTTPException(
            status_code=403,
            detail="Tu n'es pas membre de ce groupe."
        )










    messages = await group_service.get_group_messages(
        db,
        group_id,
    )
    members = await group_service.get_group_members(
        db,
        group_id,
    )

    is_admin = await group_service.is_group_admin(
        db,
        user.id,
        group_id,
    )
    flash_message = request.session.pop("flash_message", None)
    flash_type = request.session.pop("flash_type", None)

    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={
            "group": group,
            "messages": messages,
            "user": user,
            "is_admin": is_admin,
            "flash_message": flash_message,
            "flash_type": flash_type,
            "members": members,
            
        },
    )




@router.post("/groups/{group_id}/invite")
async def invite_user(
    request: Request,
    group_id: int,
    username: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    if user is None:
        return RedirectResponse("/connexion", status_code=303)

    group = await group_service.get_group(db, group_id)

    if group is None:
        raise HTTPException(
            status_code=404,
            detail="Groupe introuvable."
        )

    try:
        await group_service.invite_user_to_group(
            db,
            user.id,
            group_id,
            username
        )

    except ValueError as error:
        request.session["flash_message"] = str(error)
        request.session["flash_type"] = "error"

        return RedirectResponse(
            f"/groups/{group_id}/view",
            status_code=303,
        )

    return RedirectResponse(
        f"/groups/{group_id}/view",
        status_code=303
    )




@router.post("/groups/{group_id}/accept")
async def accept_invitation(
    request: Request,
    group_id: int,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    if user is None:
        return RedirectResponse("/connexion", status_code=303)

    try:
        await group_service.accept_group_invitation(
            db,
            user.id,
            group_id
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    return RedirectResponse("/", status_code=303)












