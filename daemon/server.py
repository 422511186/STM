import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from core.config import config_manager, TunnelConfig
from core.tunnel import tunnel_manager

app = FastAPI(title="SSH Tunnel Manager Daemon")

DEFAULT_HOST_ENV = "SSH_TUNNEL_MANAGER_HOST"
DEFAULT_PORT_ENV = "SSH_TUNNEL_MANAGER_PORT"

class SuccessResponse(BaseModel):
    success: bool
    message: str

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
            "local_port": st.get("local_port")
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
