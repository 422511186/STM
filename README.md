# SSH Tunnel Manager（SSH 隧道管理器）

一个跨平台（Windows / Linux）的 SSH 隧道管理工具，提供 **后台守护进程（Daemon）+ CLI + GUI** 三种组合能力：

- Daemon 负责在后台维护隧道生命周期（支持状态查询、启停、断线重连）
- CLI 用于脚本化与快速操作
- GUI 用于可视化管理、导入导出配置、快速启停

> 说明：本仓库内的 GUI 基于 CustomTkinter，需要桌面环境；在服务器/无桌面环境下建议使用 CLI。

---

## 特性

- 跨平台：Windows / Linux 通用
- 后台运行：关闭 CLI/GUI 后，隧道可继续在后台运行（由 Daemon 进程维持）
- 配置可迁移：配置采用 YAML 文件，可直接导出/拷贝到新设备导入复用
- 状态监控：实时显示 `inactive / connecting / active / error`，并携带错误信息
- 自动重连：隧道异常断开后，Daemon 会周期性尝试重新建立连接

---

## 架构与目录结构

- 入口：[main.py](file:///workspace/main.py)
- 配置管理：[config.py](file:///workspace/core/config.py)
- 隧道控制与重连逻辑：[tunnel.py](file:///workspace/core/tunnel.py)
- Daemon REST API：[server.py](file:///workspace/daemon/server.py)
- CLI：[main.py](file:///workspace/cli/main.py)
- GUI：[main.py](file:///workspace/gui/main.py)

Daemon 默认监听：
- `http://127.0.0.1:50051`

---

## 环境要求

- Python：建议 `3.10+`
- 依赖安装：见 [requirements.txt](file:///workspace/requirements.txt)

> 注意：由于 `sshtunnel` 与新版 `paramiko` 在部分版本组合上存在兼容性问题，本项目已将 `paramiko` 固定为 `3.3.1`（见 requirements.txt）。

---

## 安装

在项目根目录执行：

```bash
pip install -r requirements.txt
```

---

## 快速开始（推荐流程）

### 1) 启动 Daemon（后台）

```bash
python main.py cli daemon start
```

验证 Daemon 是否在线：

```bash
python main.py cli status
```

### 2) 添加一个隧道配置

示例：将远端主机 `10.0.0.10` 的 `3306`（MySQL）映射到本机 `13306`

```bash
python main.py cli add mysql_tunnel 10.0.0.10 ubuntu 13306 3306 --remote-host 127.0.0.1 --ssh-port 22 --pkey ~/.ssh/id_rsa
```

如果你使用密码登录：

```bash
python main.py cli add mysql_tunnel 10.0.0.10 ubuntu 13306 3306 --password "your_password"
```

### 3) 启动/停止隧道

```bash
python main.py cli start mysql_tunnel
python main.py cli stop mysql_tunnel
```

### 4) 查看状态

```bash
python main.py cli status
```

输出示例（状态会根据实际连接变化）：

```
- mysql_tunnel: [ACTIVE] (Local: 13306 -> Remote: 10.0.0.10)
```

---

## GUI 使用

直接运行（默认启动 GUI）：

```bash
python main.py
```

GUI 功能：
- 左侧：启动 Daemon、导入/导出配置、添加隧道
- 右侧列表：每条隧道显示状态（Active/Connecting/Error/Inactive），并提供一键 Start/Stop、Delete

如果你在无桌面环境（如 Linux 服务器）运行 GUI，会失败并提示使用 CLI，这是预期行为。

---

## CLI 命令说明

查看 CLI 总帮助：

```bash
python main.py cli --help
```

### daemon

启动后台守护进程：

```bash
python main.py cli daemon start
```

关闭后台守护进程：

```bash
python main.py cli daemon stop
```

### add / remove

添加隧道：

```bash
python main.py cli add <name> <ssh_host> <ssh_user> <local_port> <remote_port> [OPTIONS]
```

常用可选参数：
- `--remote-host`：远端目标 host（默认 `127.0.0.1`）
- `--ssh-port`：SSH 端口（默认 `22`）
- `--password`：SSH 密码（可选）
- `--pkey`：SSH 私钥路径（可选，推荐）
- `--autostart`：配置加载时自动启动（默认 false）

删除隧道：

```bash
python main.py cli remove <name>
```

### start / stop / status

```bash
python main.py cli start <name>
python main.py cli stop <name>
python main.py cli status
```

### export / load（配置迁移）

导出配置（用于迁移到其他机器）：

```bash
python main.py cli export backup.yaml
```

导入配置（会覆盖本地 config.yaml）：

```bash
python main.py cli load backup.yaml
```

---

## 配置文件（YAML）

默认配置文件为项目根目录下的 `config.yaml`（由 [config.py](file:///workspace/core/config.py) 读取/写入）。

结构示例：

```yaml
tunnels:
  mysql_tunnel:
    ssh_host: 10.0.0.10
    ssh_port: 22
    ssh_user: ubuntu
    ssh_password: null
    ssh_pkey: /home/user/.ssh/id_rsa
    local_bind_host: 127.0.0.1
    local_bind_port: 13306
    remote_bind_host: 127.0.0.1
    remote_bind_port: 3306
    autostart: false
```

字段说明（与 [TunnelConfig](file:///workspace/core/config.py#L7-L17) 对应）：
- `ssh_host / ssh_port / ssh_user`：SSH 登录目标
- `ssh_password`：密码（可选；不推荐写入配置文件）
- `ssh_pkey`：私钥路径（可选；推荐）
- `local_bind_host / local_bind_port`：本地监听
- `remote_bind_host / remote_bind_port`：远端转发目标
- `autostart`：Daemon 启动时是否自动拉起此隧道

---

## Daemon API（本地接口）

Daemon 为 CLI/GUI 提供本地 HTTP API（默认 `127.0.0.1:50051`）：

- `GET /tunnels`：获取所有隧道配置与实时状态
- `POST /tunnels/{name}/start`：启动指定隧道
- `POST /tunnels/{name}/stop`：停止指定隧道
- `POST /config/reload`：重载 config.yaml 并同步隧道列表
- `POST /shutdown`：关闭 Daemon（CLI 的 `daemon stop` 依赖此接口）

实现位置：[server.py](file:///workspace/daemon/server.py)

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

## 常见问题（Troubleshooting）

### 1) `Daemon is not running` / 无法连接 50051

- 先执行：`python main.py cli daemon start`
- 再执行：`python main.py cli status`

Daemon 只监听本机回环地址（127.0.0.1），这是刻意的安全设计，不对外网开放。

### 2) `No password or public key available!`

代表你既没有提供 `--password`，也没有提供 `--pkey`，Daemon 无法进行 SSH 认证。

解决：
- 优先使用私钥：`--pkey ~/.ssh/id_rsa`
- 或者提供密码：`--password "xxx"`

### 3) GUI 无法启动

GUI 需要桌面环境。在 Linux Server / Docker / WSL 等无桌面环境里建议直接使用 CLI。

### 4) 安全建议（强烈建议阅读）

- 尽量使用 `ssh_pkey`（私钥路径）而非 `ssh_password`
- 不要把包含 `ssh_password` 的 `config.yaml` 提交到代码仓库
- Daemon 默认只监听 127.0.0.1，不要改为 `0.0.0.0`（除非你明确知道风险并做了鉴权）

---

## 开发者说明

前台运行 Daemon（便于调试日志）：

```bash
python main.py daemon
```

---

## License

按需补充（当前未提供 License 文件）。

