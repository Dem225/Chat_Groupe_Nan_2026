import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from database import Base, engine
import models  # Important : enregistre les modèles dans SQLAlchemy

from routes.auth_routes import router as auth_router
from routes.group_routes import router as group_router
from routes.chat_routes import router as chat_router
from routes.upload_routes import router as upload_router


# =====================================
# CRÉATION DES DOSSIERS
# =====================================

Path("uploads/images").mkdir(parents=True, exist_ok=True)
Path("uploads/audios").mkdir(parents=True, exist_ok=True)
Path("static").mkdir(parents=True, exist_ok=True)


# =====================================
# INITIALISATION DE LA BASE DE DONNÉES
# =====================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield


# =====================================
# APPLICATION FASTAPI
# =====================================

app = FastAPI(
    title="Chat Group NAN",
    lifespan=lifespan,
)


# =====================================
# MIDDLEWARE DE SESSION
# =====================================

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv(
        "SESSION_SECRET",
        "cle-secrete-de-developpement-a-remplacer",
    ),
    same_site="lax",
    https_only=False,
)


# =====================================
# FICHIERS STATIQUES
# =====================================

app.mount(
    "/uploads",
    StaticFiles(directory="uploads"),
    name="uploads",
)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)


# =====================================
# INCLURE LES ROUTES
# =====================================

app.include_router(auth_router)
app.include_router(group_router)
app.include_router(chat_router)
app.include_router(upload_router)
