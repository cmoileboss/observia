"""Repository dédié aux comptes utilisateurs."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.user_model import UserModel
from repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[UserModel]):
    """Encapsule les accès en base pour les utilisateurs."""

    def __init__(self, db: Session) -> None:
        """Initialise le repository des utilisateurs."""
        super().__init__(db, UserModel)

    def get_by_email(self, email: str) -> UserModel | None:
        """Retourne un utilisateur par son adresse email."""
        return self.db.query(UserModel).filter(UserModel.email == email).first()
