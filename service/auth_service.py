from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pwdlib import PasswordHash

from models import User


password_hash = PasswordHash.recommended()


# Inscription
async def register_user(
    db: AsyncSession,
    username: str,
    email: str,
    password: str
):
    username = username.strip()
    email = email.strip().lower()

    if not username or not email or not password:
        raise ValueError("Tous les champs sont obligatoires")

    if len(password) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères")

    result = await db.execute(
        select(User).where(
            (User.email == email) | (User.username == username)
        )
    )

    if result.scalar_one_or_none():
        raise ValueError("Cet email ou ce nom d'utilisateur existe déjà")

    user = User(
        username=username,
        email=email,
        hashed_password=password_hash.hash(password)
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


# Vérifier les identifiants
async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str
):
    result = await db.execute(
        select(User).where(User.email == email.strip().lower())
    )

    user = result.scalar_one_or_none()

    if not user:
        return None

    if not password_hash.verify(password, user.hashed_password):
        return None

    return user


# Récupérer un utilisateur
async def get_user_by_id(db: AsyncSession, user_id: int):
    return await db.get(User, user_id)