# SSH Tunnel Manager - Code Wiki

## 项目概述

SSH Tunnel Manager（SSH 隧道管理器）是一个跨平台（Windows / Linux）的 SSH 隧道管理工具，提供 **后台守护进程（Daemon）+ CLI + GUI** 三种组合能力。

- **Daemon**：负责在后台维护隧道生命周期（支持状态查询、启停、断线重连）
- **CLI**：用于脚本化与快速操作
- **GUI**：用于可视化管理、导入导出配置、快速启停

---

## 目录结构

```
SSH-Tunnel-Manager/
├── main.py                    # 项目入口文件
├── config.yaml                # 配置文件（YAML格式）
├── requirements.txt           # Python依赖
├── README.md                   # 项目说明文档
│
├── core/                      # 核心模块
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   └── tunnel.py              # 隧道控制与重连逻辑
│
├── daemon/                     # 守护进程
│   ├── __init__.py
│   └── server.py              # Daemon REST API
│
├── cli/                        # 命令行界面
│   ├── __init__.py
│   └── main.py                # CLI入口
│
├── gui/                        # 图形界面
│   ├── __init__.py
│   └── main.py                # GUI入口
│
└── tests/                      # 测试文件
    ├── test_config.py
    ├── test_daemon_cli_smoke.py
    └── test_tunnel_e2e.py
```

---

## 架构设计

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户界面层                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │    GUI      │  │    CLI      │  │  直接调用    │          │
│  │ (CustomTkinter) │  │   (Typer)  │  │   (API)     │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
└─────────┼────────────────┼────────────────┼─────────────────┘
          │                │                │
          ▼                ▼                │
┌─────────────────────────────────────────────────────────────┐
│                    Daemon API 层 (FastAPI)                   │
│                http://127.0.0.1:50051                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │GET/tunnels│  │POST/start│  │POST/stop │  │POST/shutdown│ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
└───────┼────────────┼────────────┼─────────────┼────────────┘
        │            │            │             │
        ▼            ▼            ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                    TunnelManager (核心)                      │
│         管理所有 TunnelController 实例                         │
│  ┌─────────────────────────────────────────────────┐         │
│  │              TunnelController                   │         │
│  │  - 隧道生命周期管理                               │         │
│  │  - 自动重连机制                                   │         │
│  │  - 状态监控                                       │         │
│  └─────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              SSHTunnelForwarder (sshtunnel库)                │
│                    实际的SSH隧道连接                           │
└─────────────────────────────────────────────────────────────┘
```

### 数据流

1. **用户操作** → CLI/GUI/API
2. **CLI/GUI/API** → Daemon HTTP API
3. **Daemon** → TunnelManager → TunnelController
4. **TunnelController** → SSHTunnelForwarder → SSH Server

---

## 模块详解

### 1. 入口模块 (main.py)

**文件位置**: `main.py`

**功能**: 项目的统一入口，根据命令行参数分发到不同模块。

**运行方式**:

| 命令 | 说明 |
|------|------|
| `python main.py` | 启动 GUI（默认） |
| `python main.py cli ...` | 使用 CLI |
| `python main.py daemon` | 前台运行 Daemon |
| `python main.py -h` | 显示帮助 |

---

### 2. 配置管理模块 (core/config.py)

**文件位置**: `core/config.py`

#### 类定义

##### TunnelConfig

SSH 隧道的配置数据模型，继承自 `pydantic.BaseModel`。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `ssh_host` | str | - | SSH 服务器地址 |
| `ssh_port` | int | 22 | SSH 端口 |
| `ssh_user` | str | - | SSH 用户名 |
| `ssh_password` | Optional[str] | None | SSH 密码（可选） |
| `ssh_pkey` | Optional[str] | None | SSH 私钥路径（推荐） |
| `local_bind_host` | str | 127.0.0.1 | 本地绑定地址 |
| `local_bind_port` | int | - | 本地监听端口 |
| `remote_bind_host` | str | 127.0.0.1 | 远端目标地址 |
| `remote_bind_port` | int | - | 远端目标端口 |
| `autostart` | bool | False | 是否自动启动 |

##### AppConfig

应用配置，包含所有隧道配置。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `tunnels` | Dict[str, TunnelConfig] | {} | 隧道字典 |

##### ConfigManager

配置管理器，负责配置的加载、保存、导入导出。

**主要方法**:

| 方法 | 说明 |
|------|------|
| `load() -> AppConfig` | 从 config.yaml 加载配置 |
| `save()` | 保存配置到 config.yaml |
| `get_tunnel(name: str) -> Optional[TunnelConfig]` | 获取指定隧道配置 |
| `add_tunnel(name: str, config: TunnelConfig)` | 添加/更新隧道 |
| `remove_tunnel(name: str)` | 删除隧道 |
| `export_config(path: str)` | 导出配置到文件 |
| `import_config(path: str)` | 从文件导入配置 |

**全局实例**: `config_manager = ConfigManager()`

---

### 3. 隧道控制模块 (core/tunnel.py)

**文件位置**: `core/tunnel.py`

#### 状态常量 (TunnelState)

| 状态 | 值 | 说明 |
|------|------|------|
| `INACTIVE` | "inactive" | 未启动/已停止 |
| `ACTIVE` | "active" | 运行中 |
| `CONNECTING` | "connecting" | 连接中 |
| `ERROR` | "error" | 错误状态 |

#### TunnelController

单个隧道的控制器，管理隧道的启动、停止、状态监控。

**构造函数参数**:
- `name: str` - 隧道名称
- `config: TunnelConfig` - 隧道配置

**主要方法**:

| 方法 | 说明 |
|------|------|
| `start()` | 启动隧道 |
| `stop()` | 停止隧道 |
| `get_status() -> dict` | 获取隧道状态 |

**状态字典结构**:
```python
{
    "name": str,           # 隧道名称
    "state": str,          # 状态 (inactive/active/connecting/error)
    "error": str,          # 错误信息（如果有）
    "local_port": int,     # 本地端口（仅活跃时）
}
```

#### TunnelManager

管理所有隧道控制器。

**主要方法**:

| 方法 | 说明 |
|------|------|
| `sync_tunnels(config_manager)` | 同步隧道配置 |
| `start_tunnel(name: str)` | 启动指定隧道 |
| `stop_tunnel(name: str)` | 停止指定隧道 |
| `get_all_status() -> dict` | 获取所有隧道状态 |

**全局实例**: `tunnel_manager = TunnelManager()`

---

### 4. Daemon 模块 (daemon/server.py)

**文件位置**: `daemon/server.py`

使用 FastAPI 实现的 HTTP REST API 服务。

**默认配置**:
- 监听地址: `127.0.0.1` (可通过环境变量 `SSH_TUNNEL_MANAGER_HOST` 修改)
- 监听端口: `50051` (可通过环境变量 `SSH_TUNNEL_MANAGER_PORT` 修改)

#### API 端点

| 方法 | 路径 | 说明 | 请求体 | 响应 |
|------|------|------|--------|------|
| `GET` | `/tunnels` | 获取所有隧道状态 | - | `Dict[str, Any]` |
| `POST` | `/tunnels/{name}/start` | 启动隧道 | - | `SuccessResponse` |
| `POST` | `/tunnels/{name}/stop` | 停止隧道 | - | `SuccessResponse` |
| `POST` | `/config/reload` | 重载配置 | - | `SuccessResponse` |
| `POST` | `/shutdown` | 关闭 Daemon | - | `SuccessResponse` |

#### 响应模型

```python
class SuccessResponse(BaseModel):
    success: bool
    message: str
```

#### 启动方式

```python
# 方式1: 命令行
python main.py cli daemon start   # 后台运行
python main.py daemon              # 前台运行

# 方式2: Python模块
python -m daemon.server
```

---

### 5. CLI 模块 (cli/main.py)

**文件位置**: `cli/main.py`

使用 `typer` 实现的命令行界面。

#### 命令列表

| 命令 | 说明 |
|------|------|
| `daemon start` | 启动守护进程 |
| `daemon stop` | 停止守护进程 |
| `add <name> <ssh_host> <ssh_user> <local_port> <remote_port>` | 添加隧道 |
| `remove <name>` | 删除隧道 |
| `start <name> [names...]` | 启动一个或多个隧道 |
| `stop <name>` | 停止隧道 |
| `list` | 列出所有隧道 |
| `status` | 查看隧道状态 |
| `export <path>` | 导出配置 |
| `load <path>` | 导入配置 |

#### add 命令参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | - | 隧道名称 |
| `ssh_host` | str | - | SSH 服务器地址 |
| `ssh_user` | str | - | SSH 用户名 |
| `local_port` | int | - | 本地端口 |
| `remote_port` | int | - | 远端端口 |
| `--remote-host` | str | 127.0.0.1 | 远端目标地址 |
| `--ssh-port` | int | 22 | SSH 端口 |
| `--password` | str | "" | SSH 密码 |
| `--pkey` | str | "" | SSH 私钥路径 |
| `--autostart` | bool | False | 是否自动启动 |

#### 使用示例

```bash
# 启动守护进程
python main.py cli daemon start

# 添加隧道（使用私钥）
python main.py cli add mysql 10.0.0.10 ubuntu 13306 3306 --pkey ~/.ssh/id_rsa

# 添加隧道（使用密码）
python main.py cli add mysql 10.0.0.10 ubuntu 13306 3306 --password "your_password"

# 启动多个隧道
python main.py cli start tunnel1 tunnel2 tunnel3

# 查看状态
python main.py cli status
```

---

### 6. GUI 模块 (gui/main.py)

**文件位置**: `gui/main.py`

使用 `CustomTkinter` 实现的图形界面。

#### 窗口布局

```
┌────────────────────────────────────────────────────────────┐
│                    SSH 隧道管理器                            │
├──────────┬─────────────────────────────────────────────────┤
│          │                                                  │
│ 启动守护进程 │   隧道列表区域                                  │
│ 关闭守护进程 │   ┌────────────────────────────────────┐     │
│ 添加隧道    │   │ name │ 描述 │ 状态 │ 操作          │     │
│ 导入配置    │   ├────────────────────────────────────┤     │
│ 导出配置    │   │      │      │      │ 启动/停止     │     │
│          │   │      │      │      │ 编辑/删除      │     │
│          │   └────────────────────────────────────┘     │
│ 守护进程: 在线│                                                  │
├──────────┴─────────────────────────────────────────────────┤
│ 操作日志                                                   │
│ [时间戳] [级别] 消息内容                                      │
└────────────────────────────────────────────────────────────┘
```

#### 主要类

##### TunnelApp

主窗口类，继承自 `customtkinter.CTk`。

**主要方法**:

| 方法 | 说明 |
|------|------|
| `_build_sidebar()` | 构建侧边栏 |
| `_build_main_area()` | 构建主显示区域 |
| `_build_log_area()` | 构建日志区域 |
| `start_daemon()` | 启动守护进程 |
| `stop_daemon()` | 关闭守护进程 |
| `open_add_dialog(edit_name)` | 打开添加/编辑对话框 |
| `import_config()` | 导入配置 |
| `export_config()` | 导出配置 |
| `poll_daemon()` | 轮询守护进程状态（后台线程） |
| `update_tunnels_ui(data)` | 更新隧道列表UI |
| `toggle_tunnel(name, action)` | 启动/停止隧道 |
| `delete_tunnel(name)` | 删除隧道 |
| `add_log(message, level)` | 添加日志 |

#### 状态显示

| 状态 | 颜色 | 说明 |
|------|------|------|
| 活跃 | 绿色 | 隧道正在运行 |
| 连接中 | 橙色 | 隧道正在连接 |
| 错误 | 红色 | 隧道出错 |
| 未连接 | 灰色 | 隧道未启动 |

#### 日志级别

| 级别 | 颜色 | 说明 |
|------|------|------|
| INFO | 白色 | 一般信息 |
| SUCCESS | 绿色 | 成功操作 |
| WARN | 橙色 | 警告信息 |
| ERROR | 红色 | 错误信息 |

---

## 配置文件 (config.yaml)

### 示例配置

```yaml
tunnels:
  mysql_tunnel:
    ssh_host: 10.0.0.10
    ssh_port: 22
    ssh_user: ubuntu
    ssh_password: null                    # 推荐使用私钥认证
    ssh_pkey: /home/user/.ssh/id_rsa     # 私钥路径
    local_bind_host: 127.0.0.1
    local_bind_port: 13306
    remote_bind_host: 127.0.0.1
    remote_bind_port: 3306
    autostart: false
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `tunnels` | 隧道配置字典 |
| `ssh_host` | SSH 登录的目标服务器地址 |
| `ssh_port` | SSH 端口，默认 22 |
| `ssh_user` | SSH 用户名 |
| `ssh_password` | SSH 密码（可选，推荐使用 ssh_pkey） |
| `ssh_pkey` | SSH 私钥路径（可选，推荐） |
| `local_bind_host` | 本地监听地址 |
| `local_bind_port` | 本地监听端口（转发到远程的端口） |
| `remote_bind_host` | 远程目标地址（通过 SSH 隧道后访问的地址） |
| `remote_bind_port` | 远程目标端口 |
| `autostart` | Daemon 启动时是否自动启动此隧道 |

---

## 依赖关系

```
requirements.txt
├── paramiko==3.3.1       # SSH 客户端库
├── sshtunnel             # SSH 隧道封装
├── pyyaml                # YAML 配置文件解析
├── fastapi               # Web 框架（Daemon API）
├── uvicorn               # ASGI 服务器
├── requests              # HTTP 客户端
├── customtkinter         # GUI 框架
├── typer                 # CLI 框架
└── pydantic              # 数据验证
```

---

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SSH_TUNNEL_MANAGER_HOST` | 127.0.0.1 | Daemon 监听地址 |
| `SSH_TUNNEL_MANAGER_PORT` | 50051 | Daemon 监听端口 |
| `SSH_TUNNEL_MANAGER_CONFIG` | config.yaml | 配置文件路径 |

---

## 配置迁移

### 迁移步骤

**1) 导出配置**

在原电脑上执行：
```bash
python main.py cli export backup.yaml
```

**2) 复制私钥文件**

将 SSH 私钥文件（如 `~/.ssh/id_rsa`）复制到新电脑的相同或自定义位置。

**3) 导入配置**

在新电脑上执行：
```bash
python main.py cli load backup.yaml
```

**4) 修改私钥路径**（如果新电脑路径不同）

编辑 `config.yaml`，更新私钥路径为新电脑上的实际位置：
```yaml
ssh_pkey: /home/username/.ssh/id_rsa
```

### 注意事项

- **私钥文件需要单独复制**：配置文件只记录私钥路径，不会自动迁移私钥文件
- **建议使用公钥认证**：避免在配置中存储密码，配置可迁移到任何设备
- **新设备需要公钥已添加到服务器**：确保 SSH 服务器的 `~/.ssh/authorized_keys` 中包含你的公钥

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 Daemon

```bash
python main.py cli daemon start
```

### 3. 添加隧道

```bash
# 使用私钥认证
python main.py cli add mysql_tunnel 10.0.0.10 ubuntu 13306 3306 --pkey ~/.ssh/id_rsa

# 或使用密码认证
python main.py cli add mysql_tunnel 10.0.0.10 ubuntu 13306 3306 --password "your_password"
```

### 4. 启动隧道

```bash
python main.py cli start mysql_tunnel
```

### 5. 查看状态

```bash
python main.py cli status
```

### 6. 使用 GUI

```bash
python main.py
```

---

## 安全建议

1. **优先使用私钥认证**：避免在配置文件中存储密码
2. **不要提交密码到代码仓库**：将 `config.yaml` 加入 `.gitignore`
3. **Daemon 只监听本地回环地址**：默认不暴露到外网
4. **跳过主机密钥检查**：配置中 `set_keepalive` 已设置，防止长时间无响应断开

---

## 常见问题

### 1. Daemon is not running

守护进程未启动。先执行：
```bash
python main.py cli daemon start
```

### 2. No password or public key available

未提供认证凭据。确保提供 `--password` 或 `--pkey`。

### 3. GUI 无法启动

GUI 需要桌面环境。在 Linux Server / Docker / WSL 等无桌面环境里请使用 CLI。
