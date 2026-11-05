
import json
import os
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    Request,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    Form,
    HTTPException,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.sessions import SessionMiddleware

from database import Base, engine, SessionLocal, get_db
from models import User  # Charge les modèles dans les métadonnées SQLAlchemy
from service import group_service, chat_service, auth_service


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv(
        "SESSION_SECRET",
        "cle-secrete-de-developpement-a-remplacer",
    ),
    same_site="lax",
    https_only=False,  # À passer à True en production avec HTTPS
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# --------------------------------------------------
# OUTIL : RÉCUPÉRER L'UTILISATEUR CONNECTÉ
# --------------------------------------------------

async def get_current_user(request: Request, db: AsyncSession):
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    user = await auth_service.get_user_by_id(db, user_id)

    if user is None:
        request.session.clear()

    return user


# --------------------------------------------------
# INSCRIPTION
# --------------------------------------------------

@app.get("/inscription", response_class=HTMLResponse)
async def inscription_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="inscription.html",
        context={"error": None},
    )


@app.post("/inscription", response_class=HTMLResponse)
async def inscription(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await auth_service.register_user(
            db,
            username,
            email,
            password,
        )

        request.session.clear()
        request.session["user_id"] = user.id

        return RedirectResponse("/", status_code=303)

    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="inscription.html",
            context={"error": str(error)},
            status_code=400,
        )


# --------------------------------------------------
# CONNEXION
# --------------------------------------------------

@app.get("/connexion", response_class=HTMLResponse)
async def connexion_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="connexion.html",
        context={"error": None},
    )


@app.post("/connexion", response_class=HTMLResponse)
async def connexion(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.authenticate_user(
        db,
        email,
        password,
    )

    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="connexion.html",
            context={"error": "Email ou mot de passe incorrect."},
            status_code=401,
        )

    request.session.clear()
    request.session["user_id"] = user.id

    return RedirectResponse("/", status_code=303)


# --------------------------------------------------
# DÉCONNEXION
# --------------------------------------------------

@app.post("/deconnexion")
async def deconnexion(request: Request):
    request.session.clear()

    return RedirectResponse("/connexion", status_code=303)


# --------------------------------------------------
# PAGE D'ACCUEIL : LISTE DES GROUPES
# --------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def accueil(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    if user is None:
        return RedirectResponse("/connexion", status_code=303)

    groups = await group_service.get_groups(db)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "groups": groups,
            "user": user,
        },
    )


# --------------------------------------------------
# CRÉER UN GROUPE
# --------------------------------------------------

@app.post("/groups")
async def create_group(
    request: Request,
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(request, db)

    if user is None:
        return RedirectResponse("/connexion", status_code=303)

    try:
        await group_service.create_group(db, name)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    return RedirectResponse("/", status_code=303)


# --------------------------------------------------
# AFFICHER UN GROUPE
# --------------------------------------------------

@app.get("/groups/{group_id}/view", response_class=HTMLResponse)
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
            detail="Groupe introuvable",
        )

    messages = await group_service.get_group_messages(db, group_id)

    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={
            "group": group,
            "messages": messages,
            "user": user,
        },
    )


# --------------------------------------------------
# WEBSOCKET : DISCUSSION EN TEMPS RÉEL
# --------------------------------------------------

@app.websocket("/ws/{group_id}")
async def websocket_chat(
    websocket: WebSocket,
    group_id: int,
):
    # Vérifier la session de l'utilisateur
    user_id = websocket.scope.get("session", {}).get("user_id")

    if not user_id:
        await websocket.close(code=1008)
        return

    # Vérifier que l'utilisateur et le groupe existent
    async with SessionLocal() as db:
        user = await auth_service.get_user_by_id(db, user_id)
        group = await group_service.get_group(db, group_id)

    if user is None or group is None:
        await websocket.close(code=1008)
        return

    # Le nom vient du compte connecté, jamais du formulaire
    username = user.username

    await chat_service.manager.connect(websocket, group_id)

    try:
        while True:
            data = json.loads(await websocket.receive_text())

            content = str(data.get("content", "")).strip()[:4000]

            if not content:
                continue

            message = await chat_service.save_message(
                group_id,
                username,
                content,
            )

            html = templates.get_template(
                    "message.html"
                ).render(
                    message=message,
                    current_username=username
                )

            await chat_service.manager.broadcast(
                group_id,
                html,
            )

    except WebSocketDisconnect:
        pass

    finally:
        chat_service.manager.disconnect(websocket, group_id)
