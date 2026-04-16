from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from daemon.auth import decode_access_token

LOCALHOST_HOSTS = {"127.0.0.1", "::1", "localhost"}


class AuthMiddleware(BaseHTTPMiddleware):
    """Auth middleware that protects endpoints but allows localhost bypass"""

    async def dispatch(self, request: Request, call_next):
        # Paths that don't need auth
        public_paths = {
            "/auth/login",
            "/auth/status",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        }

        if request.url.path in public_paths:
            return await call_next(request)

        # Check if localhost bypass
        client_host = request.client.host if request.client else ""
        if client_host in LOCALHOST_HOSTS:
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            payload = decode_access_token(token)
            if payload:
                # Add user info to request state
                request.state.user = payload
                return await call_next(request)

        # Not authenticated
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
