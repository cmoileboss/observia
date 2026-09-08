"""Limiteur de débit (slowapi) partagé par tous les routeurs de l'API."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from services.auth_service import AuthService


def get_rate_limit_key(request: Request) -> str:
    """Limite par utilisateur authentifié si un JWT valide est présent, sinon par IP."""
    token = request.cookies.get("access_token")
    if token:
        try:
            email = AuthService.verify_access_token(token)
            return f"user:{email}"
        except ValueError:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=get_rate_limit_key)
