"""Point d'entrée de l'API Observia Emploi."""

import os
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from logging_config import configure_logging
from rate_limiting import limiter

from routers.auth_router import router as auth_router
from routers.competences_router import router as competences_router
from routers.formation_flux_mensuel_router import router as formation_flux_mensuel_router
from routers.formations_router import router as formations_router
from routers.offres_router import router as offres_router
from routers.rome_codes_router import router as rome_codes_router
from routers.main_router import main_router


load_dotenv()
configure_logging()
logger = logging.getLogger(__name__)


DATABASE_ENV_VARS = (
    "DATABASE_USER",
    "DATABASE_PASSWORD",
)

PIPELINE_ENV_VARS = (
    "CLIENT_ID",
    "SECRET_ID",
    "X-INSEE-Api-Key-Integration"
)

JWT_ENV_VARS = (
    "SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES"
)

ADMIN_ENV_VARS = (
    "ADMIN_EMAIL",
    "ADMIN_PASSWORD"
)

MANDATORY_ENV_VARS = PIPELINE_ENV_VARS + DATABASE_ENV_VARS + JWT_ENV_VARS + ADMIN_ENV_VARS


missing_vars = [name for name in MANDATORY_ENV_VARS if not os.getenv(name)]
if missing_vars:
    raise EnvironmentError(
        "Variables d'environnement non initialisées : " + ", ".join(missing_vars)
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Gère le cycle de vie de l'application FastAPI."""
    logger.info("Les variables d'environnement %s sont bien initialisées.", ", ".join(MANDATORY_ENV_VARS))
    yield


app = FastAPI(
    title="Observia Emploi API",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": False},
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.include_router(auth_router)
app.include_router(offres_router)
app.include_router(competences_router)
app.include_router(formations_router)
app.include_router(formation_flux_mensuel_router)
app.include_router(rome_codes_router)
app.include_router(main_router)


def main() -> None:
    """Démarre le serveur Uvicorn pour l'API FastAPI."""

    logger.info("Démarrage de l'API FastAPI")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        app_dir=os.path.dirname(__file__),
    )


if __name__ == "__main__":
    main()
