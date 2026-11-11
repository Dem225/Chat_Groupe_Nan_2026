from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from core.templates import templates
from service import auth_service
from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth
import os
import logging

router = APIRouter()

logger = logging.getLogger(__name__)


# ==============================
# CONFIGURATION GOOGLE OAUTH
# ==============================

load_dotenv()

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








# ==============================
# PAGE D'INSCRIPTION
# ==============================

@router.get("/inscription", response_class=HTMLResponse)
async def inscription_page(request: Request):

    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="inscription.html",
        context={"error": None},
    )


# ==============================
# TRAITEMENT DE L'INSCRIPTION
# ==============================

@router.post("/inscription", response_class=HTMLResponse)
async def inscription(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        email = await auth_service.start_registration(
            db,
            username,
            email,
            password,
        )

        request.session["pending_email"] = email

        return RedirectResponse(
            "/verification",
            status_code=303
        )

    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="inscription.html",
            context={"error": str(error)},
            status_code=400,
        )


# ==============================
# PAGE DE VERIFICATION
# ==============================
@router.get("/verification", response_class=HTMLResponse)
async def verification_page(request: Request):

    email = request.session.get("pending_email")

    if not email:
        return RedirectResponse(
            "/inscription",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="verification.html",
        context={
            "email": email,
            "error": None,
            "success": request.session.pop("verification_success", None),
        },
    )

# ==============================
# VERIFIER LE CODE
# ==============================

@router.post("/verification", response_class=HTMLResponse)
async def verification(
    request: Request,
    code: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    email = request.session.get("pending_email")

    if not email:
        return RedirectResponse(
            "/inscription",
            status_code=303
        )

    try:
        user = await auth_service.verify_registration(
            db,
            email,
            code,
        )

        request.session.clear()
        request.session["user_id"] = user.id

        return RedirectResponse("/", status_code=303)

    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="verification.html",
            context={
                "email": email,
                "error": str(error),
            },
            status_code=400,
        )




# ==============================
# RENVOYER LE CODE DE VERIFICATION
# ==============================

@router.post("/renvoyer-code", response_class=HTMLResponse)
async def renvoyer_code(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    email = request.session.get("pending_email")

    if not email:
        return RedirectResponse(
            "/inscription",
            status_code=303
        )

    try:
        await auth_service.resend_verification_code(
            db,
            email
        )

        return templates.TemplateResponse(
            request=request,
            name="verification.html",
            context={
                "email": email,
                "error": None,
                "success": "Un nouveau code a été envoyé à votre adresse email."
            }
        )

    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="verification.html",
            context={
                "email": email,
                "error": str(error),
                "success": None
            },
            status_code=400
        )

# ==============================
# PAGE DE RECUPERATION DU CODE
# ==============================

@router.get("/demander-code", response_class=HTMLResponse)
async def demander_code_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="demander_code.html",
        context={
            "error": None,
            "success": None
        }
    )


# ==============================
# TRAITEMENT DE LA RECUPERATION
# ==============================
@router.post("/demander-code", response_class=HTMLResponse)
async def demander_code(
    request: Request,
    email: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        await auth_service.resend_verification_code(db, email)

        request.session["pending_email"] = email.strip().lower()

        request.session["verification_success"] = (
            "Un nouveau code a été envoyé à votre adresse email."
        )

        return RedirectResponse(
            "/verification",
            status_code=303
        )

    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="demander_code.html",
            context={
                "error": str(error),
                "success": None
            },
            status_code=400
        )




# ==============================
# PAGE DE CONNEXION
# ==============================

@router.get("/connexion", response_class=HTMLResponse)
async def connexion_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="connexion.html",
        context={"error": None}
    )


# ==============================
# TRAITEMENT DE LA CONNEXION
# ==============================

@router.post("/connexion", response_class=HTMLResponse)
async def connexion(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await auth_service.authenticate_user(
            db,
            email,
            password
        )

        if not user:
            raise ValueError("Email ou mot de passe incorrect.")

        request.session.clear()
        request.session["user_id"] = user.id

        return RedirectResponse("/", status_code=303)

    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="connexion.html",
            context={"error": str(error)},
            status_code=400
        )


# ==============================
# DECONNEXION
# ==============================

@router.post("/deconnexion")
async def deconnexion(request: Request):
    request.session.clear()

    return RedirectResponse(
        "/connexion",
        status_code=303
    )







# ==============================
# CONNEXION AVEC GOOGLE
# ==============================

@router.get("/auth/google")
async def google_login(request: Request):

    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    if not redirect_uri:
        raise RuntimeError("GOOGLE_REDIRECT_URI est absent du .env")

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri
    )


# ==============================
# RETOUR DE GOOGLE
# ==============================

@router.get("/auth/google/callback", name="google_callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db)
):

    try:
        token = await oauth.google.authorize_access_token(request)

        user_info = token.get("userinfo")

        if not user_info:
            raise ValueError("Impossible de récupérer les informations Google.")

        if not user_info.get("email_verified"):
            raise ValueError("Votre adresse Google n'est pas vérifiée.")

        google_sub = user_info.get("sub")
        email = user_info.get("email")

        if not google_sub or not email:
            raise ValueError("Informations Google incomplètes.")

        user = await auth_service.authenticate_google_user(
            db,
            google_sub,
            email
        )

        request.session.clear()
        request.session["user_id"] = user.id

        return RedirectResponse("/", status_code=303)

    except Exception:
        logger.exception("Erreur pendant la connexion Google")
        request.session.clear()


















