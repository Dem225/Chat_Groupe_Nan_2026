from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ChatGroup, Message


async def create_group(db: AsyncSession, name: str):
    name = name.strip()

    if not name:
        raise ValueError("Le nom du groupe est obligatoire")

    result = await db.execute(
        select(ChatGroup).where(ChatGroup.name == name)
    )

    if result.scalar_one_or_none():
        raise ValueError("Ce groupe existe déjà")

    group = ChatGroup(name=name)

    db.add(group)
    await db.commit()
    await db.refresh(group)

    return group


async def get_groups(db: AsyncSession):
    result = await db.execute(select(ChatGroup))
    return result.scalars().all()


async def get_group(db: AsyncSession, group_id: int):
    return await db.get(ChatGroup, group_id)


async def get_group_messages(db: AsyncSession, group_id: int):
    result = await db.execute(
        select(Message)
        .where(Message.group_id == group_id)
        .order_by(Message.created_at)
    )

    return result.scalars().all()