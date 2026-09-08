import logging

from fastapi import Depends, HTTPException, Request, status

from sqlalchemy.orm import Session

from repositories.user_repository import UserRepository
from models.user_model import UserModel
from enums.role_enum import Role
from postgres_connection import get_db
import bcrypt
from datetime import datetime, timedelta, timezone
import jwt

from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


class AuthService:
    def __init__(self, db: Session):
        self.user_repository = UserRepository(db)

    def create_access_token(email: str) -> str:
        """Create a JWT access token for the given user email.
        Args:
            email (str): The email of the user.
        Returns:
            token (str): The encoded JWT token.
        """
        expire = datetime.now(tz=timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub": str(email),
            "iat": datetime.now(tz=timezone.utc),
            "exp": expire
        }

        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def verify_access_token(token: str) -> str:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            email = payload.get("sub")
            if email is None:
                raise ValueError("Token invalide (sub manquant)")

            return email

        except jwt.PyJWTError:
            raise ValueError("Token invalide ou expiré")
        except Exception as e:
            raise ValueError(f"Erreur lors de la vérification du token : {str(e)}")


    def login(self, email: str, password: str) -> UserModel:
        """Vérifie les identifiants et retourne un User si valides, sinon lève UnauthorizedError."""
        user = self.user_repository.get_by_email(email)
        if user is None:
            logger.warning("Tentative de connexion échouée (compte inconnu).")
            raise HTTPException(status_code=401, detail="Email ou mot de passe invalide")
        if not bcrypt.checkpw(password.encode("utf-8"), user.hash_password.encode("utf-8")):
            logger.warning("Tentative de connexion échouée pour l'utilisateur %s (mot de passe invalide).", user.id)
            raise HTTPException(status_code=401, detail="Email ou mot de passe invalide")
        logger.info("Connexion réussie pour l'utilisateur %s.", user.id)
        return user
    
    def get_all_users(self) -> list[UserModel]:
        """Retourne la liste de tous les utilisateurs."""
        return self.user_repository.get_all()

    def get_user(self, user_id: int) -> UserModel:
        """Retourne un utilisateur par son identifiant, ou lève NotFoundError."""
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        return user

    def create_user(self, email: str, password: str, role: Role = Role.USER) -> UserModel:
        """Crée un utilisateur en hachant son mot de passe avec bcrypt."""
        if self.user_repository.get_by_email(email):
            logger.warning("Tentative de création d'un compte avec un email déjà utilisé.")
            raise HTTPException(status_code=400, detail=f"Un utilisateur avec l'email {email} existe déjà")
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user = self.user_repository.add(UserModel(email=email, hash_password=hashed, role=role))
        self.user_repository.db.commit()
        self.user_repository.db.refresh(user)
        logger.info("Nouvel utilisateur créé : %s (rôle %s).", user.id, role)
        return user

    def delete_user(self, user_id: int) -> None:
        """Supprime un utilisateur. Lève NotFoundError si introuvable."""
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        self.user_repository.delete(user)
        logger.info("Utilisateur %s supprimé.", user_id)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> UserModel:
    """Résout l'utilisateur courant à partir du cookie de session JWT."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise.",
        )
    try:
        email = AuthService.verify_access_token(token)
    except ValueError as exc:
        logger.warning("Rejet d'un token JWT invalide ou expiré : %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session invalide ou expirée.",
        ) from exc

    user = UserRepository(db).get_by_email(email)
    if user is None:
        logger.warning("Token JWT valide mais utilisateur introuvable (compte supprimé ou modifié).")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable.",
        )
    return user


def require_admin(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Exige que l'utilisateur courant ait le rôle administrateur."""
    if current_user.role != Role.ADMIN:
        logger.warning(
            "Accès refusé : l'utilisateur %s (rôle %s) a tenté d'accéder à une ressource réservée aux administrateurs.",
            current_user.id,
            current_user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs.",
        )
    return current_user
