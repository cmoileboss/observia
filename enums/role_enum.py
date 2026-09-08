"""Définit les rôles utilisateurs de l'application."""

from enum import Enum


class Role(str, Enum):
    """Enumère les rôles disponibles pour un utilisateur."""

    ADMIN = "admin"
    USER = "user"
