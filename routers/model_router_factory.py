"""Fabrique de routeurs CRUD génériques pour les repositories."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from postgres_connection import get_db
from rate_limiting import limiter
from repositories.base_repository import BaseRepository
from routers.serialization import serialize_model, serialize_models
from services.auth_service import get_current_user
from services.generic_service import GenericService

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

    def get_service(db: Session = Depends(get_db)) -> GenericService[Any]:
        """Résout le service générique utilisé par les endpoints du routeur."""

        return GenericService(repository_factory(db))

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
        service: GenericService[Any] = Depends(get_service),
    ) -> dict[str, Any]:
        """Retourne une page d'entités exposées par le service."""

        page = service.list_entities(skip=skip, limit=limit)
        page["items"] = serialize_models(page["items"])
        return page

    get_all.__name__ = get_all.__qualname__ = f"get_all_{route_key}"
    router.get("/")(limiter.limit("30/minute")(get_all))
    async def get_by_id(
        request: Request,
        entity_id: str,
        service: GenericService[Any] = Depends(get_service),
    ) -> dict[str, Any]:
        """Retourne une entité sérialisée à partir de son identifiant."""

        entity = service.get_entity_by_id(entity_id)
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
