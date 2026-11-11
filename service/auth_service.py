from datetime import datetime, timedelta
import secrets
import re
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pwdlib import PasswordHash
from email_validator import validate_email, EmailNotValidError

from models import User, PendingRegistration
from service.email_service import send_verification_email

import os

from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth



password_hash = PasswordHash.recommended()


# Démarrer une inscription
async def start_registration(
    db: AsyncSession,
    username: str,
    email: str,
    password: str
):
    username = username.strip()
    email = email.strip().lower()

    if not username or not email or not password:
        raise ValueError("Tous les champs sont obligatoires")

    try:
        email_info = validate_email(
            email,
            check_deliverability=True
        )
        email = email_info.normalized

    except EmailNotValidError:
        raise ValueError("Adresse email invalide")

    if len(password) < 8:
        raise ValueError(
            "Le mot de passe doit contenir au moins 8 caractères"
        )

    result = await db.execute(
        select(User).where(
            or_(
                User.email == email,
                User.username == username
            )
        )
    )

    if result.scalar_one_or_none():
        raise ValueError(
            "Cet email ou ce nom d'utilisateur existe déjà"
        )

    # Supprimer une ancienne inscription en attente
    result = await db.execute(
        select(PendingRegistration).where(
            or_(
                PendingRegistration.email == email,
                PendingRegistration.username == username
            )
        )
    )

    for pending in result.scalars().all():
         await db.delete(pending)

    # Exécuter les suppressions avant la nouvelle insertion
    await db.flush()

    # Générer un code à 6 chiffres

    # Générer un code à 6 chiffres
    code = f"{secrets.randbelow(1_000_000):06d}"

    pending = PendingRegistration(
        username=username,
        email=email,
        hashed_password=password_hash.hash(password),
        verification_code_hash=password_hash.hash(code),
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        attempts=0
    )

    # Envoyer le code
    try:
        await send_verification_email(email, code)

        db.add(pending)
        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return email

# Renvoyer un nouveau code de vérification
async def resend_verification_code(
    db: AsyncSession,
    email: str
):
    email = email.strip().lower()

    result = await db.execute(
        select(PendingRegistration).where(
            PendingRegistration.email == email
        )
    )

    pending = result.scalar_one_or_none()

    if not pending:
        raise ValueError(
            "Aucune inscription en attente pour cette adresse email."
        )

    # Générer un nouveau code
    code = f"{secrets.randbelow(1_000_000):06d}"

    # Remplacer l'ancien code
    pending.verification_code_hash = password_hash.hash(code)

    # Prolonger sa validité de 10 minutes
    pending.expires_at = datetime.utcnow() + timedelta(minutes=10)

    # Réinitialiser les tentatives
    pending.attempts = 0

    try:
        await send_verification_email(email, code)
        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return True


# Vérifier le code et créer le compte
async def verify_registration(
    db: AsyncSession,
    email: str,
    code: str
):
    email = email.strip().lower()
    code = code.strip()

    result = await db.execute(
        select(PendingRegistration).where(
            PendingRegistration.email == email
        )
    )

    pending = result.scalar_one_or_none()

    if not pending:
        raise ValueError("Aucune inscription en attente")

    if pending.expires_at < datetime.utcnow():
        await db.delete(pending)
        await db.commit()
        raise ValueError("Le code a expiré. Recommencez l'inscription.")

    if pending.attempts >= 5:
        await db.delete(pending)
        await db.commit()
        raise ValueError("Nombre maximum de tentatives atteint")

    if not code.isdigit() or len(code) != 6:
        pending.attempts += 1
        await db.commit()
        raise ValueError("Code de confirmation incorrect")

    if not password_hash.verify(
        code,
        pending.verification_code_hash
    ):
        pending.attempts += 1
        await db.commit()
        raise ValueError("Code de confirmation incorrect")

    user = User(
        username=pending.username,
        email=pending.email,
        hashed_password=pending.hashed_password
    )

    db.add(user)
    await db.delete(pending)

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
        select(User).where(
            User.email == email.strip().lower()
        )
    )

    user = result.scalar_one_or_none()

    if not user:
        return None

    if not password_hash.verify(
        password,
        user.hashed_password
    ):
        return None

    return user


# Récupérer un utilisateur
async def get_user_by_id(
    db: AsyncSession,
    user_id: int
):
    return await db.get(User, user_id)









async def get_user_by_username(
    db: AsyncSession,
    username: str
):
    result = await db.execute(
        select(User).where(
            User.username == username.strip()
        )
    )

    return result.scalar_one_or_none()





async def authenticate_google_user(
    db: AsyncSession,
    google_sub: str,
    email: str
):
    email = email.strip().lower()

    # 1. Vérifier si le compte Google existe déjà
    result = await db.execute(
        select(User).where(User.google_sub == google_sub)
    )
    user = result.scalar_one_or_none()

    if user:
        return user

    # 2. Vérifier si l'adresse email existe déjà
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()

    if user:
        # Ne pas associer deux comptes Google différents
        if user.google_sub and user.google_sub != google_sub:
            raise ValueError(
                "Cette adresse email est déjà associée à un autre compte Google."
            )

        user.google_sub = google_sub
        await db.commit()
        await db.refresh(user)
        return user

    # 3. Générer un nom d'utilisateur disponible
    base_username = re.sub(
        r"[^a-zA-Z0-9_]",
        "_",
        email.split("@")[0]
    )[:80] or "google_user"

    username = base_username
    counter = 1

    while True:
        result = await db.execute(
            select(User).where(User.username == username)
        )

        if result.scalar_one_or_none() is None:
            break

        username = f"{base_username}_{counter}"
        counter += 1

    # 4. Créer le nouvel utilisateur
    user = User(
        username=username,
        email=email,
        hashed_password=password_hash.hash(
            secrets.token_urlsafe(48)
        ),
        google_sub=google_sub
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user





# Charger les variables d'environnement
load_dotenv()

# Configuration Google OAuth
oauth = OAuth()

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=(
        "https://accounts.google.com/.well-known/openid-configuration"
    ),
    client_kwargs={
        "scope": "openid email profile"
    }
)













