"""Service générique appliquant les règles de validation communes aux routeurs CRUD."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from fastapi import HTTPException
from sqlalchemy import inspect

from repositories.base_repository import BaseRepository

ModelT = TypeVar("ModelT")


class GenericService(Generic[ModelT]):
    """Encapsule un repository et applique les règles de validation associées."""

    def __init__(self, repository: BaseRepository[ModelT]) -> None:
        """Initialise le service avec le repository du modèle cible."""
        self.repository = repository

    def list_entities(self, skip: int, limit: int) -> dict[str, Any]:
        """Valide la pagination puis retourne une page d'entités avec le total."""
        if skip < 0:
            raise HTTPException(status_code=422, detail="skip doit être supérieur ou égal à 0")
        if limit < 1 or limit > 500:
            raise HTTPException(status_code=422, detail="limit doit être compris entre 1 et 500")

        return {
            "total": self.repository.count(),
            "skip": skip,
            "limit": limit,
            "items": self.repository.get_all(skip=skip, limit=limit),
        }

    def get_entity_by_id(self, entity_id: str) -> ModelT | None:
        """Convertit l'identifiant HTTP puis retourne l'entité correspondante."""
        parsed_id = self._parse_entity_id(entity_id)
        return self.repository.get_by_id(parsed_id)

    def _parse_entity_id(self, entity_id: str) -> Any:
        """Convertit l'identifiant HTTP vers le type de clé primaire attendu."""
        primary_keys = inspect(self.repository.model).primary_key
        if len(primary_keys) != 1:
            return entity_id

        python_type = primary_keys[0].type.python_type
        try:
            return python_type(entity_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Identifiant invalide: {entity_id}",
            ) from exc
