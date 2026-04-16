import typer
import requests
import subprocess
import sys
import os
from typing import Optional, List
from core.config import config_manager, TunnelConfig

app = typer.Typer(help="SSH 隧道管理器 CLI")
DAEMON_URL = f"http://{os.environ.get('SSH_TUNNEL_MANAGER_HOST', '127.0.0.1')}:{os.environ.get('SSH_TUNNEL_MANAGER_PORT', '50051')}"

def notify_daemon_reload():
    try:
        requests.post(f"{DAEMON_URL}/config/reload", timeout=2)
    except requests.exceptions.ConnectionError:
        pass

@app.command()
def daemon(action: str = typer.Argument(..., help="start 或 stop")):
    """管理后台守护进程"""
    if action == "start":
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        if sys.platform == "win32":
            # Windows: 使用 CREATE_NO_WINDOW 避免弹窗，DETACHED_PROCESS 让进程独立
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen([sys.executable, "-m", "daemon.server"],
                             creationflags=CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
                             env=env,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL)
        else:
            subprocess.Popen([sys.executable, "-m", "daemon.server"],
                             start_new_session=True,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             env=env)
        typer.echo("守护进程已在后台启动。")
    elif action == "stop":
        try:
            requests.post(f"{DAEMON_URL}/shutdown", timeout=2)
            typer.echo("已发送守护进程关闭请求。")
        except requests.exceptions.ConnectionError:
            typer.echo("守护进程未运行。")
    else:
        typer.echo("无效的操作，请使用 start 或 stop。")

@app.command()
def add(name: str, ssh_host: str, ssh_user: str, local_port: int, remote_port: int, remote_host: str = "127.0.0.1", ssh_port: int = 22, autostart: bool = False, password: str = "", pkey: str = "", tunnel_type: str = "local"):
    """添加新的 SSH 隧道配置"""
    conf = TunnelConfig(
        ssh_host=ssh_host,
        ssh_port=ssh_port,
        ssh_user=ssh_user,
        local_bind_port=local_port,
        remote_bind_host=remote_host,
        remote_bind_port=remote_port,
        autostart=autostart,
        tunnel_type=tunnel_type
    )
    if password:
        conf.ssh_password = password
    if pkey:
        conf.ssh_pkey = pkey

    config_manager.add_tunnel(name, conf)
    typer.echo(f"隧道 '{name}' 添加成功。")
    notify_daemon_reload()

@app.command()
def remove(name: str):
    """删除隧道配置"""
    config_manager.remove_tunnel(name)
    typer.echo(f"隧道 '{name}' 已删除。")
    notify_daemon_reload()

@app.command()
def start(names: List[str] = typer.Argument(..., help="要启动的隧道名称，支持多个")):
    """启动一个或多个隧道"""
    if not names:
        typer.echo("请指定要启动的隧道名称。")
        return

    try:
        for name in names:
            r = requests.post(f"{DAEMON_URL}/tunnels/{name}/start")
            typer.echo(r.json()["message"])
    except requests.exceptions.ConnectionError:
        typer.echo("错误：守护进程未运行，请先执行 'python main.py cli daemon start' 启动守护进程。")

@app.command()
def stop(name: str):
    """停止指定隧道"""
    try:
        r = requests.post(f"{DAEMON_URL}/tunnels/{name}/stop")
        typer.echo(r.json()["message"])
    except requests.exceptions.ConnectionError:
        typer.echo("错误：守护进程未运行。")

@app.command()
def list():
    """列出所有隧道配置"""
    tunnels = config_manager.config.tunnels
    if not tunnels:
        typer.echo("暂无隧道配置。")
        return
    for name in tunnels:
        typer.echo(f"- {name}")

@app.command()
def status():
    """列出所有隧道及其状态"""
    try:
        r = requests.get(f"{DAEMON_URL}/tunnels")
        data = r.json()
        if not data:
            typer.echo("暂无隧道配置。")
            return
        for name, info in data.items():
            st = info["status"]
            err = info["error"]
            err_msg = f" ({err})" if err else ""
            t_type = info["config"].get("tunnel_type", "local")
            type_label = "反向" if t_type == "remote" else "正向"
            typer.echo(f"- {name}: [{st.upper()}]{err_msg} ({type_label}隧道 本地: {info['config']['local_bind_port']} -> 远端: {info['config']['ssh_host']})")
    except requests.exceptions.ConnectionError:
        typer.echo("守护进程未运行，仅显示本地配置：")
        for name, info in config_manager.config.tunnels.items():
            typer.echo(f"- {name}: [未知] ({info.tunnel_type}隧道 本地端口: {info.local_bind_port} -> {info.ssh_host})")

@app.command()
def export(path: str):
    """导出配置到文件"""
    config_manager.export_config(path)
    typer.echo(f"配置已导出到 {path}")

@app.command()
def load(path: str):
    """从文件导入配置"""
    try:
        config_manager.import_config(path)
        typer.echo(f"配置已从 {path} 导入")
        notify_daemon_reload()
    except Exception as e:
        typer.echo(f"导入失败：{e}")

if __name__ == "__main__":
    app()
