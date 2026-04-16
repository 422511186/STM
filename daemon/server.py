import os
import time
import shutil
import uvicorn
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import config_manager, TunnelConfig
from core.tunnel import tunnel_manager
from daemon.auth import get_password_hash_from_env, verify_password, create_access_token
from daemon.middleware import AuthMiddleware

app = FastAPI(title="SSH Tunnel Manager Daemon")
app.add_middleware(AuthMiddleware)

# Startup time tracking
START_TIME = time.time()

# Log file configuration
LOG_FILE = "logs/tunnel.log"
MAX_LOG_LINES = 1000

DEFAULT_HOST_ENV = "SSH_TUNNEL_MANAGER_HOST"
DEFAULT_PORT_ENV = "SSH_TUNNEL_MANAGER_PORT"


class SuccessResponse(BaseModel):
    success: bool
    message: str


class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest):
    """Login with password, returns JWT token"""
    stored_hash = get_password_hash_from_env()
    if not verify_password(request.password, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": "admin"})
    return TokenResponse(access_token=token)


@app.post("/auth/logout")
def logout():
    """Logout (client should discard token)"""
    return SuccessResponse(success=True, message="Logged out")


@app.get("/auth/status")
def auth_status(request: Request):
    """Check current authentication status"""
    if hasattr(request.state, "user"):
        return {"authenticated": True, "user": request.state.user}
    return {"authenticated": False}


@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "uptime": time.time() - START_TIME}


@app.get("/logs")
def get_logs(lines: int = 100):
    """Get recent log lines"""
    if not os.path.exists(LOG_FILE):
        return {"logs": [], "total": 0}

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        all_lines = f.readlines()
        recent = all_lines[-lines:] if lines > 0 else all_lines
        return {"logs": [l.strip() for l in recent], "total": len(all_lines)}


@app.get("/config/export")
def export_config():
    """Export configuration as downloadable file"""
    config_path = os.environ.get("SSH_TUNNEL_MANAGER_CONFIG", "config.yaml")
    if not os.path.exists(config_path):
        # Create empty config
        config_manager.save()

    return FileResponse(
        config_path, media_type="application/x-yaml", filename="config.yaml"
    )


@app.post("/config/import", response_model=SuccessResponse)
async def import_config(file: UploadFile = File(...)):
    """Import configuration from uploaded file"""
    # Validate file size (1MB max)
    if file.size and file.size > 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 1MB)")

    # Read and validate YAML
    content = await file.read()
    try:
        import yaml

        data = yaml.safe_load(content)
    except ImportError:
        raise HTTPException(status_code=500, detail="YAML library not available")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {str(e)}")

    # Backup current config
    config_path = os.environ.get("SSH_TUNNEL_MANAGER_CONFIG", "config.yaml")
    if os.path.exists(config_path):
        backup_path = config_path + ".backup"
        shutil.copy2(config_path, backup_path)

    # Write new config
    with open(config_path, "wb") as f:
        f.write(content)

    # Reload
    config_manager.config = config_manager.load()
    tunnel_manager.sync_tunnels(config_manager)

    return SuccessResponse(success=True, message="Configuration imported")


class SPAFallbackMiddleware(BaseHTTPMiddleware):
    """Serve React index.html for unmatched routes (except API routes)"""

    API_PREFIXES = {
        "/auth/",
        "/tunnels",
        "/config/",
        "/logs",
        "/health",
        "/docs",
        "/openapi",
        "/redoc",
    }

    async def dispatch(self, request: Request, call_next):
        # Let API routes through
        for prefix in self.API_PREFIXES:
            if request.url.path.startswith(prefix):
                return await call_next(request)

        # For GET requests to non-API paths, serve index.html
        if request.method == "GET":
            index_path = "web/dist/index.html"
            if os.path.exists(index_path):
                return FileResponse(index_path)

        return await call_next(request)


# Add SPA fallback middleware (after auth middleware)
app.add_middleware(SPAFallbackMiddleware)


@app.on_event("startup")
def startup_event():
    # 启动时同步配置并启动设置为自启的隧道
    tunnel_manager.sync_tunnels(config_manager)


@app.get("/tunnels", response_model=Dict[str, Any])
def get_tunnels():
    status = tunnel_manager.get_all_status()
    result = {}
    for name, t_conf in config_manager.config.tunnels.items():
        st = status.get(name, {})
        result[name] = {
            "config": t_conf.model_dump(),
            "status": st.get("state", "inactive"),
            "error": st.get("error", ""),
            "local_port": st.get("local_port"),
        }
    return result


@app.post("/tunnels/{name}/start", response_model=SuccessResponse)
def start_tunnel(name: str):
    if name not in config_manager.config.tunnels:
        raise HTTPException(status_code=404, detail="Tunnel not found")
    tunnel_manager.start_tunnel(name)
    return SuccessResponse(success=True, message=f"Started tunnel {name}")


@app.post("/tunnels/{name}/stop", response_model=SuccessResponse)
def stop_tunnel(name: str):
    if name not in config_manager.config.tunnels:
        raise HTTPException(status_code=404, detail="Tunnel not found")
    tunnel_manager.stop_tunnel(name)
    return SuccessResponse(success=True, message=f"Stopped tunnel {name}")


@app.post("/config/reload", response_model=SuccessResponse)
def reload_config():
    config_manager.config = config_manager.load()
    tunnel_manager.sync_tunnels(config_manager)
    return SuccessResponse(success=True, message="Configuration reloaded")


@app.post("/shutdown", response_model=SuccessResponse)
def shutdown():
    import os
    import signal
    import threading

    def commit_suicide():
        import time

        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGTERM)

    threading.Thread(target=commit_suicide).start()
    return SuccessResponse(success=True, message="Shutting down daemon")


def run_server(host=None, port=None):
    import os

    if host is None:
        host = os.environ.get(DEFAULT_HOST_ENV, "127.0.0.1")
    if port is None:
        port = int(os.environ.get(DEFAULT_PORT_ENV, "50051"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
