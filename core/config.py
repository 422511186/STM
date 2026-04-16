import yaml
import os
import shutil
from typing import Dict, Optional
from pydantic import BaseModel, Field

DEFAULT_CONFIG_ENV = "SSH_TUNNEL_MANAGER_CONFIG"

class TunnelConfig(BaseModel):
    ssh_host: str
    ssh_port: int = 22
    ssh_user: str
    ssh_password: Optional[str] = None
    ssh_pkey: Optional[str] = None
    local_bind_host: str = "127.0.0.1"
    local_bind_port: int
    remote_bind_host: str = "127.0.0.1"
    remote_bind_port: int
    autostart: bool = False

class AppConfig(BaseModel):
    tunnels: Dict[str, TunnelConfig] = Field(default_factory=dict)

class ConfigManager:
    def __init__(self, config_path: Optional[str] = None):
        if not config_path:
            config_path = os.environ.get(DEFAULT_CONFIG_ENV, "config.yaml")
        self.config_path = config_path
        self.config = self.load()

    def load(self) -> AppConfig:
        if not os.path.exists(self.config_path):
            return AppConfig()
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return AppConfig(**data)

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self.config.model_dump(exclude_none=True), f, default_flow_style=False, allow_unicode=True)

    def get_tunnel(self, name: str) -> Optional[TunnelConfig]:
        return self.config.tunnels.get(name)

    def add_tunnel(self, name: str, tunnel_config: TunnelConfig):
        self.config.tunnels[name] = tunnel_config
        self.save()

    def remove_tunnel(self, name: str):
        if name in self.config.tunnels:
            del self.config.tunnels[name]
            self.save()

    def export_config(self, export_path: str):
        if not os.path.exists(self.config_path):
            self.save()
        shutil.copy2(self.config_path, export_path)

    def import_config(self, import_path: str):
        if not os.path.exists(import_path):
            raise FileNotFoundError(f"Import file {import_path} does not exist.")
        shutil.copy2(import_path, self.config_path)
        self.config = self.load()

# 全局默认配置管理器实例
config_manager = ConfigManager()
