
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))


class ChatGroup(Base):
    __tablename__ = "chat_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str] = mapped_column(Text)
    username: Mapped[str] = mapped_column(String(100))
    group_id: Mapped[int] = mapped_column(ForeignKey("chat_groups.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    image_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    audio_path: Mapped[str | None] = mapped_column(
    String(500),
    nullable=True
    )





class PendingRegistration(Base):
    __tablename__ = "pending_registrations"

    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column(
        String(100),
        unique=True
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True
    )

    hashed_password: Mapped[str] = mapped_column(String(255))

    verification_code_hash: Mapped[str] = mapped_column(
        String(255)
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime
    )

    attempts: Mapped[int] = mapped_column(default=0)