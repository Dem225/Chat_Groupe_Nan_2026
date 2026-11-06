from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from core.templates import templates
from service import auth_service


router = APIRouter()


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
# PAGE DE CONNEXION
# ==============================

@router.get("/connexion", response_class=HTMLResponse)
async def connexion_page(request: Request):

    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="connexion.html",
        context={"error": None},
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
    user = await auth_service.authenticate_user(
        db,
        email,
        password,
    )

    if user is None:
        return templates.TemplateResponse(
            request=request,
            name="connexion.html",
            context={
                "error": "Email ou mot de passe incorrect."
            },
            status_code=401,
        )

    request.session.clear()
    request.session["user_id"] = user.id

    return RedirectResponse("/", status_code=303)


# ==============================
# DECONNEXION
# ==============================

@router.post("/deconnexion")
async def deconnexion(request: Request):

    request.session.clear()

    return RedirectResponse("/connexion", status_code=303)