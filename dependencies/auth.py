from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from service import auth_service


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    user = await auth_service.get_user_by_id(db, user_id)

    if user is None:
        request.session.clear()

    return user