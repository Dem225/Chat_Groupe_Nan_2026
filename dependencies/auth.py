
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from service import auth_service


async def get_optional_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Retourne l'utilisateur connecté ou None."""
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    user = await auth_service.get_user_by_id(db, user_id)

    if user is None:
        request.session.clear()
        return None

    return user


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Exige une session utilisateur valide."""
    user = await get_optional_user(request, db)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vous devez être connecté pour accéder à cette ressource.",
        )

    return user
