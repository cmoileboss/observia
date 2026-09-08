"""Routes d'authentification et de gestion des comptes utilisateurs."""
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from enums.role_enum import Role
from models.user_model import UserModel
from postgres_connection import get_db
from rate_limiting import limiter
from services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    AuthService,
    get_current_user,
    require_admin,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class UserOut(BaseModel):
    """Représentation publique d'un utilisateur (sans le mot de passe)."""

    id: int
    email: str
    role: Role

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    """Payload de création d'un compte utilisateur."""

    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=64)


class LoginRequest(BaseModel):
    """Payload de connexion d'un utilisateur."""

    email: str
    password: str


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Construit le service d'authentification à partir de la session courante."""

    return AuthService(db)


@router.get("/", response_model=list[UserOut])
@limiter.limit("30/minute")
async def get_all(
    request: Request,
    service: AuthService = Depends(get_auth_service),
    _current_user=Depends(require_admin),
):
    """Retourne la liste de tous les utilisateurs (admin uniquement)."""

    return service.get_all_users()


@router.get("/me", response_model=UserOut)
@limiter.limit("30/minute")
async def get_me(request: Request, current_user: UserModel = Depends(get_current_user)):
    """Retourne les informations du compte de l'utilisateur connecté (droit d'accès RGPD)."""

    return current_user


@router.delete("/me", status_code=204)
@limiter.limit("5/minute")
async def delete_me(
    request: Request,
    response: Response,
    service: AuthService = Depends(get_auth_service),
    current_user: UserModel = Depends(get_current_user),
):
    """Supprime le compte de l'utilisateur connecté (droit à l'effacement RGPD)."""

    service.delete_user(current_user.id)
    response.delete_cookie(key="access_token")


@router.get("/{user_id}", response_model=UserOut)
@limiter.limit("30/minute")
async def get_by_id(
    request: Request,
    user_id: int,
    service: AuthService = Depends(get_auth_service),
    _current_user=Depends(require_admin),
):
    """Retourne un utilisateur par son identifiant (admin uniquement)."""

    return service.get_user(user_id)


@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit("5/minute")
async def register(
    request: Request,
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
):
    """Crée un nouveau compte utilisateur avec le rôle 'user' par défaut."""

    return service.create_user(payload.email, payload.password, Role.USER)


@router.post("/login", response_model=UserOut)
@limiter.limit("10/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    service: AuthService = Depends(get_auth_service),
):
    """Authentifie un utilisateur et dépose le JWT dans un cookie httpOnly."""

    user = service.login(payload.email, payload.password)
    token = AuthService.create_access_token(user.email)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return user

@router.post("/logout")
@limiter.limit("30/minute")
async def logout(request: Request, response: Response):
    """Supprime le cookie d'authentification."""
    response.delete_cookie(key="access_token")
    return {"detail": "Déconnexion réussie"}