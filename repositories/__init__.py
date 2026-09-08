"""Expose les repositories utilises par l'application."""

from repositories.base_repository import BaseRepository
from repositories.correspondance_formation_repository import (
    FormationRepository as FormationDataRepository,
)
from repositories.francetravail_repository import (
    CompetenceRepository,
    OffreFormationRepository,
    OffreRepository,
)
from repositories.user_repository import UserRepository

__all__ = [
    "BaseRepository",
    "OffreRepository",
    "OffreFormationRepository",
    "CompetenceRepository",
    "FormationDataRepository",
    "UserRepository",
]
