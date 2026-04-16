import threading
import time
import logging
import socket
import paramiko
from sshtunnel import SSHTunnelForwarder, BaseSSHTunnelForwarderError
from core.config import TunnelConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TunnelState:
    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"
    CONNECTING = "connecting"

def _make_ssh_client(config: TunnelConfig):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if config.ssh_pkey:
        client.connect(
            config.ssh_host,
            port=config.ssh_port,
            username=config.ssh_user,
            key_filename=config.ssh_pkey,
            look_for_keys=False,
            password=None,
        )
    elif config.ssh_password:
        client.connect(
            config.ssh_host,
            port=config.ssh_port,
            username=config.ssh_user,
            password=config.ssh_password,
            look_for_keys=False,
        )
    else:
        client.connect(
            config.ssh_host,
            port=config.ssh_port,
            username=config.ssh_user,
        )
    return client

class ReverseTunnelController:
    """反向隧道控制器：在 SSH 服务器上监听端口，将流量转发到本地服务"""
    def __init__(self, name: str, config: TunnelConfig):
        self.name = name
        self.config = config
        self.server = None
        self.transport = None
        self.client = None
        self.state = TunnelState.INACTIVE
        self.error_message = ""
        self._stop_event = threading.Event()
        self._monitor_thread = None

    def start(self):
        if self.state in [TunnelState.ACTIVE, TunnelState.CONNECTING]:
            return
        self.state = TunnelState.CONNECTING
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._run_and_monitor, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        self._stop_event.set()
        self._close()
        self.state = TunnelState.INACTIVE

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "error": self.error_message,
            "local_port": self.config.remote_bind_port if self.state == TunnelState.ACTIVE else None
        }

    def _close(self):
        try:
            if self.transport:
                self.transport.close()
        except Exception:
            pass
        try:
            if self.client:
                self.client.close()
        except Exception:
            pass
        self.transport = None
        self.client = None

    def _run_and_monitor(self):
        while not self._stop_event.is_set():
            self._close()
            try:
                self.client = _make_ssh_client(self.config)
                self.transport = self.client.get_transport()
                self.transport.set_keepalive(5.0)
                # request_port_forward(listen_port, reverse=True) 实现 -R 反向转发
                listen_port = self.transport.request_port_forward(
                    self.config.remote_bind_port,
                    reverse=True
                )
                self.state = TunnelState.ACTIVE
                self.error_message = ""
                logger.info(f"Reverse tunnel {self.name} started on remote port {listen_port}")

                # 等待 stop 事件或传输关闭
                while not self._stop_event.is_set():
                    if not self.transport.is_active():
                        break
                    time.sleep(1)

            except Exception as e:
                self.state = TunnelState.ERROR
                self.error_message = str(e)
                logger.error(f"Reverse tunnel {self.name} error: {e}")
                self._close()

            if not self._stop_event.is_set():
                # 10 秒后重试
                for _ in range(10):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)

        # Cleanup when stopped
        self._close()
        self.state = TunnelState.INACTIVE

class TunnelController:
    def __init__(self, name: str, config: TunnelConfig):
        self.name = name
        self.config = config
        self.server = None
        self.state = TunnelState.INACTIVE
        self.error_message = ""
        self._stop_event = threading.Event()
        self._monitor_thread = None

    def start(self):
        if self.state in [TunnelState.ACTIVE, TunnelState.CONNECTING]:
            return
        self.state = TunnelState.CONNECTING
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._run_and_monitor, daemon=True)
        self._monitor_thread.start()

    def stop(self):
        self._stop_event.set()
        if self.server:
            try:
                self.server.stop()
            except Exception:
                pass
        self.state = TunnelState.INACTIVE

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state,
            "error": self.error_message,
            "local_port": self.config.local_bind_port if self.state == TunnelState.ACTIVE else None
        }

    def _run_and_monitor(self):
        while not self._stop_event.is_set():
            try:
                if not self.server or not self.server.is_active:
                    self.state = TunnelState.CONNECTING
                    kwargs = {
                        "ssh_address_or_host": (self.config.ssh_host, self.config.ssh_port),
                        "ssh_username": self.config.ssh_user,
                        "local_bind_address": (self.config.local_bind_host, self.config.local_bind_port),
                        "remote_bind_address": (self.config.remote_bind_host, self.config.remote_bind_port),
                        # skip host key checking for ease of use in migration
                        "set_keepalive": 5.0,
                        "mute_exceptions": True,
                    }
                    if self.config.ssh_password:
                        kwargs["ssh_password"] = self.config.ssh_password
                    if self.config.ssh_pkey:
                        kwargs["ssh_pkey"] = self.config.ssh_pkey

                    self.server = SSHTunnelForwarder(**kwargs)
                    self.server.start()
                    self.state = TunnelState.ACTIVE
                    self.error_message = ""
                    logger.info(f"Tunnel {self.name} started successfully.")

            except BaseSSHTunnelForwarderError as e:
                self.state = TunnelState.ERROR
                self.error_message = str(e)
                logger.error(f"Tunnel {self.name} SSH error: {e}")
                self.server = None
            except Exception as e:
                self.state = TunnelState.ERROR
                self.error_message = str(e)
                logger.error(f"Tunnel {self.name} unexpected error: {e}")
                self.server = None

            # Sleep and check periodically
            for _ in range(10):
                if self._stop_event.is_set():
                    break
                time.sleep(1)

        # Cleanup when stopped
        if self.server:
            self.server.stop()
            self.server = None
        self.state = TunnelState.INACTIVE

class TunnelManager:
    """Manages all tunnel controllers."""
    def __init__(self):
        self.controllers: dict[str, TunnelController] = {}

    def sync_tunnels(self, config_manager):
        """Sync controllers with current config."""
        current_names = set(config_manager.config.tunnels.keys())
        running_names = set(self.controllers.keys())

        # Stop and remove deleted tunnels
        for name in running_names - current_names:
            self.controllers[name].stop()
            del self.controllers[name]

        # Add or update tunnels
        for name, t_conf in config_manager.config.tunnels.items():
            if name not in self.controllers:
                if t_conf.tunnel_type == "remote":
                    self.controllers[name] = ReverseTunnelController(name, t_conf)
                else:
                    self.controllers[name] = TunnelController(name, t_conf)
                if t_conf.autostart:
                    self.controllers[name].start()
            else:
                # If config changed, restart with correct controller type
                if self.controllers[name].config != t_conf:
                    self.controllers[name].stop()
                    if t_conf.tunnel_type == "remote":
                        self.controllers[name] = ReverseTunnelController(name, t_conf)
                    else:
                        self.controllers[name] = TunnelController(name, t_conf)
                    if t_conf.autostart:
                        self.controllers[name].start()
                # If tunnel_type changed, recreate controller
                old_is_remote = isinstance(self.controllers[name], ReverseTunnelController)
                new_is_remote = t_conf.tunnel_type == "remote"
                if old_is_remote != new_is_remote:
                    self.controllers[name].stop()
                    if new_is_remote:
                        self.controllers[name] = ReverseTunnelController(name, t_conf)
                    else:
                        self.controllers[name] = TunnelController(name, t_conf)
                    if t_conf.autostart:
                        self.controllers[name].start()

    def start_tunnel(self, name: str):
        if name in self.controllers:
            self.controllers[name].start()

    def stop_tunnel(self, name: str):
        if name in self.controllers:
            self.controllers[name].stop()

    def get_all_status(self) -> dict:
        return {name: ctrl.get_status() for name, ctrl in self.controllers.items()}

tunnel_manager = TunnelManager()
