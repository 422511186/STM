import os
import sys
import subprocess
import requests
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll, Vertical
from textual.widgets import Header, Footer, Static, Button, RichLog, Label, Input, Select
from textual.screen import ModalScreen
from textual import work
from textual.message import Message

from core.config import config_manager, TunnelConfig

DAEMON_URL = f"http://{os.environ.get('SSH_TUNNEL_MANAGER_HOST', '127.0.0.1')}:{os.environ.get('SSH_TUNNEL_MANAGER_PORT', '50051')}"

class InputModal(ModalScreen[str]):
    def __init__(self, prompt: str, default: str = ""):
        super().__init__()
        self.prompt = prompt
        self.default = default

    def compose(self) -> ComposeResult:
        with Vertical(id="input-dialog"):
            yield Label(self.prompt)
            yield Input(value=self.default, id="input-field")
            with Horizontal(id="input-buttons"):
                yield Button("确认", variant="primary", id="btn-ok")
                yield Button("取消", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-ok":
            self.dismiss(self.query_one("#input-field", Input).value)
        else:
            self.dismiss(None)

class ConfirmModal(ModalScreen[bool]):
    def __init__(self, prompt: str):
        super().__init__()
        self.prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(self.prompt)
            with Horizontal(id="confirm-buttons"):
                yield Button("确认", variant="error", id="btn-confirm-ok")
                yield Button("取消", variant="default", id="btn-confirm-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-confirm-ok":
            self.dismiss(True)
        else:
            self.dismiss(False)

class TunnelFormModal(ModalScreen[dict]):
    def __init__(self, edit_name=None, initial_data=None):
        super().__init__()
        self.edit_name = edit_name
        self.initial_data = initial_data or {}

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="tunnel-form"):
            yield Label("编辑隧道" if self.edit_name else "添加隧道", id="form-title")
            
            yield Label("名称")
            yield Input(value=self.initial_data.get("name", ""), id="f_name", disabled=bool(self.edit_name))
            
            yield Label("隧道类型")
            yield Select([("正向 (Local)", "local"), ("反向 (Remote)", "remote")], value=self.initial_data.get("tunnel_type", "local"), id="f_tunnel_type")
            
            yield Label("SSH 主机")
            yield Input(value=self.initial_data.get("ssh_host", ""), id="f_ssh_host")
            
            yield Label("SSH 端口")
            yield Input(value=str(self.initial_data.get("ssh_port", "22")), id="f_ssh_port")
            
            yield Label("SSH 用户")
            yield Input(value=self.initial_data.get("ssh_user", ""), id="f_ssh_user")
            
            yield Label("SSH 密码 (留空使用私钥)")
            yield Input(value=self.initial_data.get("ssh_password", ""), id="f_ssh_password", password=True)
            
            yield Label("私钥路径")
            yield Input(value=self.initial_data.get("ssh_pkey", ""), id="f_ssh_pkey")
            
            yield Label("本地端口")
            yield Input(value=str(self.initial_data.get("local_bind_port", "")), id="f_local_port")
            
            yield Label("远端主机")
            yield Input(value=self.initial_data.get("remote_bind_host", "127.0.0.1"), id="f_remote_host")
            
            yield Label("远端端口")
            yield Input(value=str(self.initial_data.get("remote_bind_port", "")), id="f_remote_port")

            with Horizontal(id="form-buttons"):
                yield Button("保存", variant="primary", id="btn-save")
                yield Button("取消", variant="default", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-save":
            try:
                data = {
                    "name": self.query_one("#f_name", Input).value,
                    "tunnel_type": self.query_one("#f_tunnel_type", Select).value,
                    "ssh_host": self.query_one("#f_ssh_host", Input).value,
                    "ssh_port": int(self.query_one("#f_ssh_port", Input).value or "22"),
                    "ssh_user": self.query_one("#f_ssh_user", Input).value,
                    "ssh_password": self.query_one("#f_ssh_password", Input).value or None,
                    "ssh_pkey": self.query_one("#f_ssh_pkey", Input).value or None,
                    "local_bind_port": int(self.query_one("#f_local_port", Input).value or "0"),
                    "remote_bind_host": self.query_one("#f_remote_host", Input).value,
                    "remote_bind_port": int(self.query_one("#f_remote_port", Input).value or "0"),
                }
                self.dismiss(data)
            except ValueError as e:
                self.app.log_msg(f"表单验证失败: {e}", "ERROR")
        elif event.button.id == "btn-cancel":
            self.dismiss(None)

class TunnelCard(Static):
    class Action(Message):
        def __init__(self, tunnel_name: str, action: str):
            self.tunnel_name = tunnel_name
            self.action = action
            super().__init__()

    def __init__(self, name: str, config: dict, status: str):
        super().__init__()
        self.tunnel_name = name
        self.config = config
        self.status = status

    def compose(self) -> ComposeResult:
        with Horizontal(classes="tunnel-card"):
            with Vertical(classes="tunnel-info"):
                yield Label(f"[b]{self.tunnel_name}[/b] - {self.status.upper()}", classes=f"status-{self.status}")
                t_type = self.config.get("tunnel_type", "local")
                type_lbl = "反向" if t_type == "remote" else "正向"
                yield Label(f"{type_lbl} {self.config.get('local_bind_port')} -> {self.config.get('ssh_host')}:{self.config.get('ssh_port')} -> {self.config.get('remote_bind_host')}:{self.config.get('remote_bind_port')}")
            
            with Horizontal(classes="tunnel-actions"):
                if self.status in ("active", "connecting", "error"):
                    yield Button("停止", variant="warning", id=f"btn-stop-{self.tunnel_name}")
                else:
                    yield Button("启动", variant="success", id=f"btn-start-{self.tunnel_name}")
                yield Button("编辑", id=f"btn-edit-{self.tunnel_name}")
                yield Button("删除", variant="error", id=f"btn-delete-{self.tunnel_name}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id.split("-")[1]
        self.post_message(self.Action(self.tunnel_name, action))

class TunnelManagerApp(App):
    CSS = '''
    Screen {
        layout: grid;
        grid-size: 4 4;
        grid-rows: 1fr 10;
        grid-columns: 30 1fr;
    }
    #sidebar {
        row-span: 2;
        width: 30;
        padding: 1 2;
        border-right: solid $border;
        background: $panel;
    }
    #sidebar Button {
        width: 100%;
        margin-bottom: 1;
    }
    #main-area {
        column-span: 3;
        padding: 1 2;
    }
    #log-area {
        column-span: 3;
        height: 10;
        border-top: solid $border;
        background: $surface;
    }
    .tunnel-card {
        border: solid $border;
        padding: 1;
        margin-bottom: 1;
        height: auto;
    }
    .tunnel-info {
        width: 1fr;
    }
    .tunnel-actions {
        width: auto;
        align: right middle;
    }
    .tunnel-actions Button {
        margin-left: 1;
    }
    .status-active { color: $success; }
    .status-connecting { color: $warning; }
    .status-error { color: $error; }
    .status-offline { color: $text-muted; }
    .status-inactive { color: $text-muted; }
    
    InputModal {
        align: center middle;
    }
    #input-dialog {
        width: 40;
        height: auto;
        border: thick $primary;
        background: $panel;
        padding: 1 2;
    }
    #input-buttons {
        margin-top: 1;
        align: right middle;
    }
    #input-buttons Button {
        margin-left: 1;
    }
    
    ConfirmModal {
        align: center middle;
    }
    #confirm-dialog {
        width: 40;
        height: auto;
        border: thick $error;
        background: $panel;
        padding: 1 2;
    }
    #confirm-buttons {
        margin-top: 1;
        align: right middle;
    }
    #confirm-buttons Button {
        margin-left: 1;
    }
    
    TunnelFormModal {
        align: center middle;
    }
    #tunnel-form {
        width: 60;
        height: 80%;
        border: thick $primary;
        background: $panel;
        padding: 1 2;
    }
    #form-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #form-buttons {
        margin-top: 1;
        align: right middle;
    }
    #form-buttons Button {
        margin-left: 1;
    }
    '''

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="sidebar"):
            yield Label("⚡ SSH 隧道", classes="text-bold", id="logo-label")
            yield Label("守护进程: 检查中...", id="daemon-status")
            yield Static("")
            yield Button("启动守护进程", id="btn-start-daemon")
            yield Button("关闭守护进程", id="btn-stop-daemon", variant="warning")
            yield Static("")
            yield Button("添加隧道", id="btn-add-tunnel", variant="primary")
            yield Button("导入配置", id="btn-import")
            yield Button("导出配置", id="btn-export")
            yield Static("")
            yield Button("退出", id="btn-quit", variant="error")
            
        with VerticalScroll(id="main-area"):
            yield Label("暂无隧道数据...", id="empty-state")
            
        with Container(id="log-area"):
            yield RichLog(id="logs", highlight=True, markup=True)
            
        yield Footer()

    def on_mount(self) -> None:
        self.title = "SSH 隧道管理器"
        self.poll_daemon()
        self.log_msg("TUI 已启动", "INFO")

    def log_msg(self, msg: str, level: str = "INFO"):
        log_widget = self.query_one("#logs", RichLog)
        colors = {"INFO": "cyan", "SUCCESS": "green", "WARN": "yellow", "ERROR": "red"}
        color = colors.get(level, "white")
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_widget.write(f"[[{color}]{level}[/]] [{timestamp}] {msg}")

    @work(exclusive=True, thread=True)
    def poll_daemon(self) -> None:
        import time
        was_offline = False
        while True:
            try:
                r = requests.get(f"{DAEMON_URL}/tunnels", timeout=2)
                data = r.json()
                if was_offline:
                    self.call_from_thread(self.log_msg, "守护进程已连接", "SUCCESS")
                    was_offline = False
                self.call_from_thread(self.update_daemon_status, "在线", "green")
                self.call_from_thread(self.update_tunnels, data)
            except requests.exceptions.ConnectionError:
                if not was_offline:
                    self.call_from_thread(self.log_msg, "守护进程连接断开", "WARN")
                    was_offline = True
                self.call_from_thread(self.update_daemon_status, "离线", "red")
                local_data = {
                    name: {"config": conf.model_dump(), "status": "offline"}
                    for name, conf in config_manager.config.tunnels.items()
                }
                self.call_from_thread(self.update_tunnels, local_data)
            except Exception:
                pass
            time.sleep(2)

    def update_daemon_status(self, status: str, color: str):
        lbl = self.query_one("#daemon-status", Label)
        lbl.update(f"守护进程: [{color}]{status}[/]")

    def update_tunnels(self, data: dict):
        main_area = self.query_one("#main-area")
        
        current_names = set(data.keys())
        existing_cards = {card.tunnel_name: card for card in main_area.query(TunnelCard)}
        existing_names = set(existing_cards.keys())

        if not current_names:
            if not main_area.query("#empty-state"):
                main_area.mount(Label("暂无隧道数据...", id="empty-state"))
        else:
            for el in main_area.query("#empty-state"):
                el.remove()

        for name in existing_names - current_names:
            existing_cards[name].remove()

        for name in current_names:
            info = data[name]
            config = info.get("config", {})
            status = info.get("status", "offline")
            
            if name not in existing_cards:
                main_area.mount(TunnelCard(name, config, status))
            else:
                card = existing_cards[name]
                if card.status != status or card.config != config:
                    card.status = status
                    card.config = config
                    card.remove()
                    main_area.mount(TunnelCard(name, config, status))

    def notify_daemon(self):
        try:
            requests.post(f"{DAEMON_URL}/config/reload", timeout=2)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-start-daemon":
            self.start_daemon()
        elif btn_id == "btn-stop-daemon":
            self.stop_daemon()
        elif btn_id == "btn-add-tunnel":
            self.push_screen(TunnelFormModal(), self.handle_tunnel_form)
        elif btn_id == "btn-import":
            self.push_screen(InputModal("请输入导入文件路径:"), self.handle_import)
        elif btn_id == "btn-export":
            self.push_screen(InputModal("请输入导出文件路径:", "tunnels_backup.yaml"), self.handle_export)
        elif btn_id == "btn-quit":
            self.exit()

    def start_daemon(self):
        self.log_msg("正在启动守护进程...", "INFO")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        if sys.platform == "win32":
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(
                [sys.executable, "-m", "daemon.server"],
                creationflags=CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                [sys.executable, "-m", "daemon.server"],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
            )
        self.log_msg("守护进程启动命令已发送", "INFO")

    def stop_daemon(self):
        try:
            requests.post(f"{DAEMON_URL}/shutdown", timeout=3)
            self.log_msg("关闭守护进程请求已发送", "INFO")
            self.update_daemon_status("离线", "red")
        except requests.exceptions.ConnectionError:
            self.log_msg("守护进程未运行", "WARN")
        except Exception as e:
            self.log_msg(f"关闭守护进程失败: {e}", "ERROR")

    def handle_import(self, path: str | None) -> None:
        if path:
            try:
                config_manager.import_config(path)
                self.notify_daemon()
                self.log_msg(f"配置已从 {path} 导入", "SUCCESS")
            except Exception as e:
                self.log_msg(f"配置导入失败: {e}", "ERROR")

    def handle_export(self, path: str | None) -> None:
        if path:
            try:
                config_manager.export_config(path)
                self.log_msg(f"配置已导出到 {path}", "SUCCESS")
            except Exception as e:
                self.log_msg(f"配置导出失败: {e}", "ERROR")

    def handle_tunnel_form(self, data: dict | None) -> None:
        if data:
            name = data.pop("name")
            if not name:
                self.log_msg("隧道名称不能为空", "ERROR")
                return
            
            try:
                conf = TunnelConfig(**data)
                if name in config_manager.config.tunnels:
                    config_manager.remove_tunnel(name)
                config_manager.add_tunnel(name, conf)
                self.notify_daemon()
                self.log_msg(f"隧道 '{name}' 保存成功", "SUCCESS")
            except Exception as e:
                self.log_msg(f"保存隧道失败: {e}", "ERROR")

    def on_tunnel_card_action(self, message: TunnelCard.Action) -> None:
        name = message.tunnel_name
        action = message.action
        
        if action in ("start", "stop"):
            try:
                r = requests.post(f"{DAEMON_URL}/tunnels/{name}/{action}", timeout=2)
                self.log_msg(f"隧道 '{name}' {action}操作已执行", "SUCCESS" if r.status_code == 200 else "ERROR")
            except requests.exceptions.ConnectionError:
                self.log_msg(f"无法连接守护进程，隧道 '{name}' {action}失败", "ERROR")
            except Exception as e:
                self.log_msg(f"隧道 '{name}' {action}失败: {e}", "ERROR")
        elif action == "delete":
            def do_delete(confirm: bool | None):
                if confirm:
                    config_manager.remove_tunnel(name)
                    self.notify_daemon()
                    self.log_msg(f"隧道 '{name}' 已删除", "INFO")
            self.push_screen(ConfirmModal(f"确定要删除隧道 {name} 吗？"), do_delete)
        elif action == "edit":
            t = config_manager.config.tunnels.get(name)
            if t:
                initial_data = t.model_dump()
                initial_data["name"] = name
                self.push_screen(TunnelFormModal(edit_name=name, initial_data=initial_data), self.handle_tunnel_form)

def run_app():
    app = TunnelManagerApp()
    app.run()

if __name__ == "__main__":
    run_app()
