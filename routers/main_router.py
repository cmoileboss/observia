"""Routes principales exposant les opérations métier du backend."""

import logging

from fastapi import APIRouter, Request
from fastapi.params import Depends
from sqlalchemy.orm import Session

from postgres_connection import get_db
from rate_limiting import limiter
from services.auth_service import get_current_user, require_admin
from services.service import Service

logger = logging.getLogger(__name__)

main_router = APIRouter(prefix="/api", tags=["API"], dependencies=[Depends(get_current_user)])


def get_service(db: Session = Depends(get_db)) -> Service:
    """Construit le service métier à partir de la session courante."""

    return Service(db)


@main_router.post("/populatedb")
@limiter.limit("2/minute;10/hour")
async def populate_database(
    request: Request,
    service: Service = Depends(get_service),
    _current_user=Depends(require_admin),
):
    """Lance le pipeline d'initialisation de la base de données (admin uniquement)."""
    logger.info("Initialisation de la base de données déclenchée par l'administrateur %s.", _current_user.id)
    service.populate_database()
    logger.info("Initialisation de la base de données terminée (déclenchée par %s).", _current_user.id)
    return {"message": "Base de données initialisée avec succès."}


@main_router.get("/job/{job_id}/formations")
@limiter.limit("60/minute")
async def get_best_organismes_for_job_id(
    request: Request,
    job_id: int,
    service: Service = Depends(get_service),
):
    """Retourne les formations pertinentes pour l'offre demandée."""

    return service.get_formations_by_offre_id(job_id)

@main_router.get("/bestskills")
@limiter.limit("30/minute")
async def get_best_skills(request: Request, service: Service = Depends(get_service)):
    """Retourne les compétences les plus fréquentes dans les offres importées."""

    return service.get_best_skills()


@main_router.get("/formations/historique")
@limiter.limit("30/minute")
async def get_nb_offers(
    request: Request,
    region: str | None = None,
    quarter: str | None = None,
    service: Service = Depends(get_service),
):
    """Retourne les indicateurs agrégés des formations par région et trimestre."""

    return service.count_formation_entries_by_region_and_quarter(region, quarter)
