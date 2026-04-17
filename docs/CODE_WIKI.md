# SSH Tunnel Manager - Code Wiki

## 1. 项目整体架构 (Project Architecture)

本项目是一个跨平台的 SSH 隧道管理工具，旨在提供灵活的隧道启停、重连以及配置管理能力。项目采用了 **后台守护进程（Daemon）+ 多客户端（CLI / GUI / Web UI）** 的架构模式。

### 架构分层
* **核心业务层 (Core)**：负责 SSH 隧道的建立、心跳维持、异常重连逻辑，以及 YAML 配置文件的持久化读写。
* **服务层 (Daemon)**：基于 FastAPI 提供的后台守护进程，将核心业务能力封装为 REST API 暴露给各类客户端。
* **表现层 (Clients)**：
  * **CLI**：基于 Typer 实现，适合 Linux/无界面环境的快捷命令操作。
  * **GUI**：基于 CustomTkinter 实现的桌面端可视化工具。
  * **Web UI**：基于 React + Vite 实现的浏览器端可视化管理界面。

```mermaid
graph TD
    A[Web UI (React)] -->|REST API| D(Daemon Server / FastAPI)
    B[CLI (Typer)] -->|REST API| D
    C[GUI (CustomTkinter)] -->|REST API| D
    D -->|操作| E[TunnelManager]
    D -->|读写| F[ConfigManager]
    E --> G[SSHTunnelForwarder / Paramiko]
    F --> H[(config.yaml)]
```

---

## 2. 主要模块职责 (Module Responsibilities)

| 目录/模块 | 主要职责 |
|---|---|
| `core/` | 核心逻辑层。处理隧道生命周期、多隧道状态同步，以及配置的序列化与反序列化。 |
| `daemon/` | 服务层。提供后台持续运行的能力，暴露 RESTful API 供前端/GUI/CLI 调用。 |
| `cli/` | 命令行入口。提供终端下的添加、删除、启停、查看状态等快捷指令。 |
| `gui/` | 桌面端入口。提供面向桌面用户的窗口化管理能力。 |
| `web/` | Web 前端。浏览器中访问的隧道管理后台，支持查看状态、启停隧道与日志审计。 |
| `main.py` | 系统的统一入口文件。用于解析启动参数并派发给具体的模块（如 CLI, Daemon, GUI）。 |

---

## 3. 关键类与函数说明 (Key Classes & Functions)

### 3.1 核心层 (`core/`)

#### `core.config.ConfigManager`
**文件**: [core/config.py](file:///workspace/core/config.py)
* **职责**：全局配置管理器，单例模式。负责加载和保存 `config.yaml`。
* **关键方法**：
  * `load() / save()`: 读写 YAML 配置文件。
  * `add_tunnel() / remove_tunnel()`: 更新内存中的隧道配置字典，并落盘。
  * `export_config() / import_config()`: 配置文件迁移功能。

#### `core.tunnel.TunnelManager`
**文件**: [core/tunnel.py](file:///workspace/core/tunnel.py)
* **职责**：隧道控制器统筹类，管理所有隧道的实例，维护内存中的隧道集合。
* **关键方法**：
  * `sync_tunnels()`: 根据当前 `config_manager` 的最新配置，同步增删改对应的控制器。
  * `start_tunnel() / stop_tunnel()`: 触发指定隧道的启动/停止事件。
  * `get_all_status()`: 汇集所有运行中控制器的状态，返回给 Daemon。

#### `core.tunnel.TunnelController` / `ReverseTunnelController`
**文件**: [core/tunnel.py](file:///workspace/core/tunnel.py)
* **职责**：负责单一隧道的建立、断线重连和状态上报。
* **说明**：
  * `TunnelController`: 包装了 `sshtunnel.SSHTunnelForwarder`，实现正向隧道（`-L`）。
  * `ReverseTunnelController`: 包装了 `paramiko.SSHClient`，调用 `request_port_forward(reverse=True)` 实现反向隧道（`-R`）。
  * 均包含一个 `_run_and_monitor` 后台线程，负责在遇到网络断开时（10秒延迟）自动重试。

### 3.2 守护进程 (`daemon/`)

#### `daemon.server.app`
**文件**: [daemon/server.py](file:///workspace/daemon/server.py)
* **职责**：FastAPI 应用实例。
* **关键路由**：
  * `POST /auth/login`: 密码校验并返回 JWT Token。
  * `GET /tunnels`: 返回所有隧道的配置及其当前状态。
  * `POST /tunnels/{name}/start|stop`: 控制隧道启停。
  * `POST /config/reload`: 重载配置文件并同步到 `TunnelManager`。

### 3.3 客户端与界面

#### `cli.main.app`
**文件**: [cli/main.py](file:///workspace/cli/main.py)
* **职责**：基于 Typer 构建的 CLI 解析器。
* **关键逻辑**：通过 `requests` 模块向 Daemon `http://127.0.0.1:50051` 发送控制指令。如果是 `daemon start` 则通过 `subprocess.Popen` 在后台拉起 `daemon.server`。

#### `gui.main.TunnelApp`
**文件**: [gui/main.py](file:///workspace/gui/main.py)
* **职责**：继承自 `customtkinter.CTk` 的主窗体类。
* **关键逻辑**：内置了一个后台线程 `poll_daemon`，每隔 2 秒通过 HTTP 轮询 Daemon 状态，并实时刷新 GUI 的 UI 列表（如状态小圆点、启停按钮）。

---

## 4. 依赖关系 (Dependencies)

### Python 后端
项目强依赖以下库（详见 [requirements.txt](file:///workspace/requirements.txt)）：
* `paramiko` (固定为 `3.3.1`): 底层 SSH 协议实现，用于连接与反向隧道。
* `sshtunnel`: 用于封装和建立稳定的正向隧道。
* `fastapi` & `uvicorn`: 构建和运行后台 Daemon HTTP API。
* `customtkinter`: 用于构建现代化的跨平台 GUI 界面。
* `typer`: 用于快速构建好用的 CLI 命令行。
* `pydantic` & `pyyaml`: 用于配置文件的校验与读写。

### Node 前端 (`web/`)
* `react` & `vite`: 前端页面渲染与构建工具。
* `tailwindcss`: 前端样式与布局。

---

## 5. 项目运行方式 (How to Run)

### 5.1 环境准备
1. 安装 Python 后端依赖:
   ```bash
   pip install -r requirements.txt
   ```
2. 安装 Web 前端依赖 (如果需要 Web UI):
   ```bash
   cd web && npm install
   ```

### 5.2 启动守护进程 (Daemon)
所有的功能都需要 Daemon 在后台运行来维持隧道连接。
```bash
python main.py cli daemon start
```

### 5.3 启动不同形态的客户端
**方式一：使用 CLI (命令行)**
```bash
# 查看状态
python main.py cli status
# 添加正向隧道
python main.py cli add my_tunnel 10.0.0.10 root 8080 80 --pkey ~/.ssh/id_rsa
# 启动/停止
python main.py cli start my_tunnel
python main.py cli stop my_tunnel
```

**方式二：使用 GUI (桌面端)**
直接运行根目录的 `main.py` 即可唤起 CustomTkinter 界面（需具备桌面环境）。
```bash
python main.py
```

**方式三：使用 Web UI (浏览器)**
启动前端开发服务器：
```bash
cd web
npm run dev
```
打开浏览器访问 `http://localhost:3000` 即可使用 Web 页面管理后台。
