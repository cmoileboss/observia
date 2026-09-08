"""Fabrique de routeurs CRUD génériques pour les repositories."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from postgres_connection import get_db
from rate_limiting import limiter
from repositories.base_repository import BaseRepository
from routers.serialization import serialize_model, serialize_models
from services.auth_service import get_current_user

logger = logging.getLogger(__name__)

RepositoryFactory = Callable[[Session], BaseRepository[Any]]


def create_model_router(
    *,
    prefix: str,
    tags: list[str],
    repository_factory: RepositoryFactory,
) -> APIRouter:
    """Construit un routeur CRUD minimal pour un repository donné."""

    router = APIRouter(prefix=prefix, tags=tags, dependencies=[Depends(get_current_user)])

    def parse_entity_id(repository: BaseRepository[Any], entity_id: str) -> Any:
        """Convertit l'identifiant HTTP vers le type de clé primaire attendu."""

        primary_keys = inspect(repository.model).primary_key
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

    def get_repository(db: Session = Depends(get_db)) -> BaseRepository[Any]:
        """Résout le repository utilisé par les endpoints du routeur."""

        return repository_factory(db)

    # slowapi indexe ses quotas par "module.__name__" de la fonction décorée : comme cette
    # fabrique produit des fonctions toutes nommées "get_all"/"get_by_id", tous les routeurs
    # générés (formations, offres, compétences, ...) partageaient le même compteur 30/minute
    # au lieu d'un quota indépendant par routeur. On force donc un nom unique par préfixe
    # avant d'appliquer le décorateur de limitation.
    route_key = prefix.strip("/").replace("/", "_") or "root"

    async def get_all(
        request: Request,
        skip: int = 0,
        limit: int = 100,
        repository: BaseRepository[Any] = Depends(get_repository),
    ) -> dict[str, Any]:
        """Retourne une page d'entités exposées par le repository."""

        if skip < 0:
            raise HTTPException(status_code=422, detail="skip doit être supérieur ou égal à 0")
        if limit < 1 or limit > 500:
            raise HTTPException(status_code=422, detail="limit doit être compris entre 1 et 500")

        return {
            "total": repository.count(),
            "skip": skip,
            "limit": limit,
            "items": serialize_models(repository.get_all(skip=skip, limit=limit)),
        }

    get_all.__name__ = get_all.__qualname__ = f"get_all_{route_key}"
    router.get("/")(limiter.limit("30/minute")(get_all))
    async def get_by_id(
        request: Request,
        entity_id: str,
        repository: BaseRepository[Any] = Depends(get_repository),
    ) -> dict[str, Any]:
        """Retourne une entité sérialisée à partir de son identifiant."""

        entity = repository.get_by_id(parse_entity_id(repository, entity_id))
        if entity is None:
            logger.info(
                "Ressource introuvable pour le préfixe %s et l'identifiant %s.",
                prefix,
                entity_id,
            )
            raise HTTPException(
                status_code=404,
                detail=f"Ressource introuvable pour l'identifiant {entity_id}",
            )
        return serialize_model(entity)

    get_by_id.__name__ = get_by_id.__qualname__ = f"get_by_id_{route_key}"
    router.get("/{entity_id}")(limiter.limit("30/minute")(get_by_id))

    return router
