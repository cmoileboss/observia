"""Modèle SQLAlchemy représentant un compte utilisateur."""

from sqlalchemy import Column
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Integer, String

from enums.role_enum import Role
from postgres_connection import Base


class UserModel(Base):
    """Représente un utilisateur et son rôle d'accès à l'API."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hash_password = Column(String, nullable=False)
    role = Column(
        SqlEnum(Role, name="user_role", values_callable=lambda enum: [role.value for role in enum]),
        nullable=False,
        default=Role.USER,
    )
