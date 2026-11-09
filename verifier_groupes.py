import asyncio
from database import SessionLocal
from service.group_service import get_groups, get_group_messages


async def main():
    async with SessionLocal() as db:
        groups = await get_groups(db)

        for group in groups:
            messages = await get_group_messages(db, group.id)

            print(
                f"Groupe : {group.name} | "
                f"ID : {group.id} | "
                f"Messages : {len(messages)}"
            )


asyncio.run(main())