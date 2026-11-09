from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ChatGroup, Message, GroupMember , User

async def create_group(db: AsyncSession, name: str, user_id: int):
    name = name.strip()

    if not name:
        raise ValueError("Le nom du groupe est obligatoire")

    result = await db.execute(
        select(ChatGroup).where(ChatGroup.name == name)
    )

    if result.scalar_one_or_none():
        raise ValueError("Ce groupe existe déjà")

    # Créer le groupe
    group = ChatGroup(name=name)

    db.add(group)
    await db.flush()

    # Ajouter automatiquement le créateur comme administrateur
    membership = GroupMember(
        user_id=user_id,
        group_id=group.id,
        role="admin",
        status="accepted"
    )

    db.add(membership)

    await db.commit()
    await db.refresh(group)

    return group





async def get_groups(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(ChatGroup)
        .join(GroupMember)
        .where(
            GroupMember.user_id == user_id,
            GroupMember.status == "accepted"
        )
    )

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









async def is_group_member(
    db: AsyncSession,
    user_id: int,
    group_id: int
):
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.user_id == user_id,
            GroupMember.group_id == group_id,
            GroupMember.status == "accepted"
        )
    )

    return result.scalar_one_or_none() is not None






async def is_group_admin(
    db: AsyncSession,
    user_id: int,
    group_id: int
):
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.user_id == user_id,
            GroupMember.group_id == group_id,
            GroupMember.role == "admin",
            GroupMember.status == "accepted"
        )
    )

    return result.scalar_one_or_none() is not None




async def invite_user_to_group(
    db: AsyncSession,
    admin_user_id: int,
    group_id: int,
    username: str
):
    # Vérifier que l'utilisateur est administrateur
    is_admin = await is_group_admin(
        db,
        admin_user_id,
        group_id
    )

    if not is_admin:
        raise ValueError(
            "Seul un administrateur peut inviter des utilisateurs."
        )

    # Rechercher l'utilisateur à inviter
    result = await db.execute(
        select(User).where(
            User.username == username.strip()
        )
    )

    invited_user = result.scalar_one_or_none()

    if invited_user is None:
        raise ValueError("Utilisateur introuvable.")

    # Vérifier si une association existe déjà
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.user_id == invited_user.id,
            GroupMember.group_id == group_id
        )
    )

    existing_member = result.scalar_one_or_none()

    if existing_member:
        raise ValueError(
            "Cet utilisateur est déjà membre ou possède une invitation."
        )

    # Créer l'invitation
    invitation = GroupMember(
        user_id=invited_user.id,
        group_id=group_id,
        role="member",
        status="invited"
    )

    db.add(invitation)
    await db.commit()

    return invitation




async def accept_group_invitation(
    db: AsyncSession,
    user_id: int,
    group_id: int
):
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.user_id == user_id,
            GroupMember.group_id == group_id,
            GroupMember.status == "invited"
        )
    )

    invitation = result.scalar_one_or_none()

    if invitation is None:
        raise ValueError(
            "Aucune invitation en attente pour ce groupe."
        )

    invitation.status = "accepted"

    await db.commit()

    return invitation



async def get_pending_invitations(
    db: AsyncSession,
    user_id: int
):
    result = await db.execute(
        select(GroupMember, ChatGroup)
        .join(ChatGroup, GroupMember.group_id == ChatGroup.id)
        .where(
            GroupMember.user_id == user_id,
            GroupMember.status == "invited"
        )
    )

    return result.all()


async def get_group_members(
    db: AsyncSession,
    group_id: int
):
    result = await db.execute(
        select(User, GroupMember)
        .join(GroupMember, User.id == GroupMember.user_id)
        .where(
            GroupMember.group_id == group_id,
            GroupMember.status == "accepted"
        )
    )

    return result.all()












