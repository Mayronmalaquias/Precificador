"""Autenticacao global da API.

Fecha a API (antes publica) exigindo, em TODA requisicao, um destes:

  1. Header  ``X-API-KEY: <API_SECRET_KEY>``  -> chave estatica da aplicacao
     (compartilhada por web + app mobile).
  2. Header  ``Authorization: Bearer <jwt>``  -> JWT por usuario, emitido no
     login e assinado com ``JWT_SECRET`` (HS256).

Basta UM dos dois ser valido (regra "OU"). Requisicao sem credencial valida
recebe HTTP 401.

Rotas liberadas: preflight CORS (OPTIONS), ``/health``, docs/swagger.
"""

import hmac
import time

import jwt
from flask import current_app, g, jsonify, request

# Rotas publicas (sem auth): healthcheck de monitoramento e Swagger UI.
_PUBLIC_EXACT = {"/", "/swagger.json", "/favicon.ico"}
_PUBLIC_PREFIXES = ("/docs", "/swaggerui")


def _is_public(path: str, api_prefix: str) -> bool:
    if path in _PUBLIC_EXACT:
        return True
    if path == "/health" or path == f"{api_prefix}/health":
        return True
    for prefix in _PUBLIC_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return True
    return False


def _check_api_key() -> bool:
    """Valida o header X-API-KEY contra API_SECRET_KEY (tempo constante)."""
    expected = current_app.config.get("API_SECRET_KEY") or ""
    if not expected:
        return False
    provided = request.headers.get("X-API-KEY", "")
    # hmac.compare_digest evita timing attack na comparacao.
    return bool(provided) and hmac.compare_digest(str(provided), str(expected))


def _check_bearer_jwt() -> bool:
    """Valida um JWT no header Authorization: Bearer <token>."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth[len("Bearer "):].strip()
    if not token:
        return False
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET"],
            algorithms=[current_app.config["JWT_ALGORITHM"]],
        )
    except jwt.PyJWTError:
        return False
    # Disponibiliza o usuario autenticado para as rotas (opcional).
    g.jwt_payload = payload
    return True


def gerar_jwt(subject, extra_claims=None, expires_in=None) -> str:
    """Emite um JWT assinado (usado no login para devolver o Bearer token)."""
    agora = int(time.time())
    ttl = expires_in if expires_in is not None else current_app.config["JWT_EXPIRES_SECONDS"]
    payload = {"sub": str(subject), "iat": agora, "exp": agora + int(ttl)}
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(
        payload,
        current_app.config["JWT_SECRET"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )
    # PyJWT >= 2 ja retorna str; PyJWT 1.x retorna bytes.
    return token.decode("utf-8") if isinstance(token, bytes) else token


def register_auth_middleware(app):
    """Registra o guard global (before_request) na app."""
    api_prefix = app.config["API_PREFIX"].rstrip("/")

    if app.config.get("AUTH_ENABLED", True) and not app.config.get("API_SECRET_KEY"):
        app.logger.warning(
            "AUTH_ENABLED=true mas API_SECRET_KEY vazia: apenas Bearer JWT sera aceito."
        )

    @app.before_request
    def _require_auth():
        # Preflight CORS do navegador nunca carrega credenciais.
        if request.method == "OPTIONS":
            return None
        # Kill-switch: permite reabrir a API sem redeploy (AUTH_ENABLED=false).
        if not current_app.config.get("AUTH_ENABLED", True):
            return None
        if _is_public(request.path, api_prefix):
            return None
        if _check_api_key() or _check_bearer_jwt():
            return None
        return (
            jsonify(
                {
                    "error": "Nao autorizado",
                    "message": "Requisicao sem X-API-KEY valida ou Bearer token.",
                }
            ),
            401,
        )
