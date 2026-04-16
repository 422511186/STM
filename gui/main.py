import customtkinter as ctk
import requests
import threading
import time
from tkinter import messagebox, filedialog
from core.config import config_manager, TunnelConfig
import subprocess
import sys
import os
from datetime import datetime

DAEMON_URL = f"http://{os.environ.get('SSH_TUNNEL_MANAGER_HOST', '127.0.0.1')}:{os.environ.get('SSH_TUNNEL_MANAGER_PORT', '50051')}"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class ToolTip:
    """简单的鼠标悬停提示类"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = ctk.CTkLabel(self.tooltip_window, text=self.text, font=ctk.CTkFont(size=11),
                             fg_color=("gray90", "gray20"), text_color=("gray30", "gray70"))
        label.grid(row=0, column=0, padx=5, pady=3)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

class TunnelApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SSH 隧道管理器")
        self.geometry("1000x700")

        # grid layout: row0=主内容, row1=日志; column0=侧边栏, column1=主面板
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)  # 日志区固定
        self.grid_columnconfigure(0, weight=0)  # 侧边栏固定宽度
        self.grid_columnconfigure(1, weight=1)

        self.tunnels_data = {}
        self.frames = {}
        self.log_lines = []
        self.max_log_lines = 100

        self._build_sidebar()
        self._build_main_area()
        self._build_log_area()

        # Start background polling
        self.running = True
        threading.Thread(target=self.poll_daemon, daemon=True).start()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="SSH 隧道管理器", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.btn_start_daemon = ctk.CTkButton(self.sidebar, text="启动守护进程", command=self.start_daemon)
        self.btn_start_daemon.grid(row=1, column=0, padx=20, pady=10)

        self.btn_stop_daemon = ctk.CTkButton(self.sidebar, text="关闭守护进程", command=self.stop_daemon, fg_color="orange", hover_color="darkorange")
        self.btn_stop_daemon.grid(row=2, column=0, padx=20, pady=10)

        self.btn_add = ctk.CTkButton(self.sidebar, text="添加隧道", command=self.open_add_dialog)
        self.btn_add.grid(row=3, column=0, padx=20, pady=10)

        self.btn_import = ctk.CTkButton(self.sidebar, text="导入配置", command=self.import_config)
        self.btn_import.grid(row=4, column=0, padx=20, pady=10)

        self.btn_export = ctk.CTkButton(self.sidebar, text="导出配置", command=self.export_config)
        self.btn_export.grid(row=5, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self.sidebar, text="守护进程: 检查中...", text_color="gray")
        self.status_label.grid(row=7, column=0, padx=20, pady=20, sticky="s")

    def _build_main_area(self):
        self.main_frame = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=(10, 0))
        self.main_frame.grid_columnconfigure(0, weight=1)

    def _build_log_area(self):
        self.log_frame = ctk.CTkFrame(self, corner_radius=0)
        self.log_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 10))
        self.log_frame.grid_propagate(False)  # 防止frame收缩
        self.log_frame.grid_rowconfigure(0, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)

        self.log_title = ctk.CTkLabel(self.log_frame, text="操作日志", font=ctk.CTkFont(size=14, weight="bold"))
        self.log_title.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.log_text = ctk.CTkTextbox(self.log_frame, font=ctk.CTkFont(size=10))
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.log_text.configure(state="disabled")

    def add_log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color_map = {"INFO": "white", "SUCCESS": "green", "ERROR": "red", "WARN": "orange"}
        color = color_map.get(level, "white")
        self.log_lines.append(f"[{timestamp}] [{level}] {message}")
        if len(self.log_lines) > self.max_log_lines:
            self.log_lines.pop(0)
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", "\n".join(self.log_lines))
        self.log_text.configure(state="disabled")

    def _build_main_area(self):
        self.main_frame = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)

    def start_daemon(self):
        self.add_log("正在启动守护进程...", "INFO")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.getcwd()
        if sys.platform == "win32":
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
        self.add_log("守护进程启动命令已发送", "INFO")
        messagebox.showinfo("守护进程", "守护进程已在后台启动。")

    def stop_daemon(self):
        try:
            r = requests.post(f"{DAEMON_URL}/shutdown", timeout=3)
            self.add_log("关闭守护进程请求已发送", "INFO")
            self.status_label.configure(text="守护进程: 离线", text_color="red")
            messagebox.showinfo("守护进程", "守护进程关闭请求已发送。")
        except requests.exceptions.ConnectionError:
            self.add_log("守护进程未运行", "WARN")
            messagebox.showinfo("守护进程", "守护进程未运行。")
        except Exception as e:
            self.add_log(f"关闭守护进程失败：{e}", "ERROR")
            messagebox.showerror("错误", f"关闭守护进程失败：{e}")

    def import_config(self):
        path = filedialog.askopenfilename(filetypes=[("YAML 文件", "*.yaml"), ("所有文件", "*.*")])
        if path:
            try:
                config_manager.import_config(path)
                self.notify_daemon()
                self.add_log(f"配置已从 {path} 导入", "SUCCESS")
                messagebox.showinfo("成功", "配置导入成功。")
            except Exception as e:
                self.add_log(f"配置导入失败：{e}", "ERROR")
                messagebox.showerror("错误", f"导入失败：{e}")

    def export_config(self):
        path = filedialog.asksaveasfilename(defaultextension=".yaml", filetypes=[("YAML 文件", "*.yaml")])
        if path:
            try:
                config_manager.export_config(path)
                self.add_log(f"配置已导出到 {path}", "SUCCESS")
                messagebox.showinfo("成功", "配置导出成功。")
            except Exception as e:
                self.add_log(f"配置导出失败：{e}", "ERROR")
                messagebox.showerror("错误", f"导出失败：{e}")

    def notify_daemon(self):
        try:
            requests.post(f"{DAEMON_URL}/config/reload", timeout=2)
        except:
            pass

    def open_add_dialog(self, edit_name=None):
        dialog = ctk.CTkToplevel(self)
        is_edit = edit_name is not None
        dialog.title("编辑隧道" if is_edit else "添加隧道")
        dialog.geometry("550x720")

        entries = {}
        fields = ["name", "tunnel_type", "ssh_host", "ssh_port", "ssh_user", "ssh_password", "ssh_pkey", "local_bind_port", "remote_bind_host", "remote_bind_port"]
        defaults = {"ssh_port": "22", "tunnel_type": "local", "remote_bind_host": "127.0.0.1"}
        labels_cn = {
            "name": "名称",
            "tunnel_type": "隧道类型",
            "ssh_host": "SSH 主机",
            "ssh_port": "SSH 端口",
            "ssh_user": "SSH 用户",
            "ssh_password": "SSH 密码",
            "ssh_pkey": "私钥路径",
            "local_bind_port": "本地端口",
            "remote_bind_host": "远端主机",
            "remote_bind_port": "远端端口"
        }
        field_hints = {
            "name": "隧道的唯一标识名称",
            "tunnel_type": "local=正向(访问远程), remote=反向(暴露本地)",
            "ssh_host": "SSH服务器地址（IP或域名）",
            "ssh_port": "SSH服务端口，默认22",
            "ssh_user": "SSH登录用户名",
            "ssh_password": "密码认证（推荐使用私钥）",
            "ssh_pkey": "私钥文件路径，如 ~/.ssh/id_rsa",
            "local_bind_port": "正向:本机监听端口 | 反向:本机服务端口",
            "remote_bind_host": "正向:远端目标主机 | 反向:通常127.0.0.1",
            "remote_bind_port": "正向:远端目标端口 | 反向:SSH服务器监听端口"
        }
        tunnel_type_values = ["local", "remote"]

        # 帮助说明文本
        help_texts = {
            "local": """【正向隧道 (local)】访问远程服务器上的服务
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
流向: 本机监听端口 → SSH服务器 → 远端目标端口

示例: 本机13306 → SSH服务器 → 远端MySQL 3306
      访问本机13306 = 访问远程数据库

字段说明:
• 本地端口: 本机监听端口（你访问的端口）
• 远端端口: 远程服务的实际端口
• 远端主机: 目标服务所在主机""",
            "remote": """【反向隧道 (remote)】让外网访问本机服务
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
流向: SSH服务器监听端口 → 本机服务端口

示例: SSH服务器8080 → 本机Web应用8080
      外网访问SSH服务器:8080 = 访问你本机

字段说明:
• 本地端口: 本机服务端口（你的应用端口）
• 远端端口: SSH服务器对外监听端口
• 远端主机: 通常为127.0.0.1

前提: SSH服务器需开启 GatewayPorts"""
        }

        # 帮助说明框
        help_frame = ctk.CTkFrame(dialog, fg_color=("gray90", "gray20"))
        help_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

        help_label = ctk.CTkLabel(help_frame, text=help_texts["local"], font=ctk.CTkFont(size=11),
                                   justify="left", text_color=("gray30", "gray70"))
        help_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Pre-fill values if editing
        initial_values = {}
        if is_edit and edit_name in config_manager.config.tunnels:
            t = config_manager.config.tunnels[edit_name]
            initial_values = {
                "name": edit_name,
                "tunnel_type": t.tunnel_type,
                "ssh_host": t.ssh_host,
                "ssh_port": str(t.ssh_port),
                "ssh_user": t.ssh_user,
                "ssh_password": t.ssh_password or "",
                "ssh_pkey": t.ssh_pkey or "",
                "local_bind_port": str(t.local_bind_port),
                "remote_bind_host": t.remote_bind_host,
                "remote_bind_port": str(t.remote_bind_port)
            }
            # 设置初始帮助文本
            help_label.configure(text=help_texts.get(t.tunnel_type, help_texts["local"]))

        # 更新帮助文本的回调函数
        def update_help_text(choice):
            help_label.configure(text=help_texts.get(choice, help_texts["local"]))

        for i, field in enumerate(fields):
            row_idx = i + 1  # row 0 是帮助框
            lbl = ctk.CTkLabel(dialog, text=labels_cn.get(field, field))
            lbl.grid(row=row_idx, column=0, padx=10, pady=5, sticky="e")

            # 字段提示（鼠标悬停提示）
            hint_label = ctk.CTkLabel(dialog, text="?", width=20, text_color="gray")
            hint_label.grid(row=row_idx, column=2, padx=5, pady=5, sticky="w")
            # 创建提示tooltip
            ToolTip(hint_label, field_hints.get(field, ""))

            if field == "tunnel_type":
                opt = ctk.CTkOptionMenu(dialog, values=tunnel_type_values, width=200, command=update_help_text)
                if is_edit and "tunnel_type" in initial_values:
                    opt.set(initial_values["tunnel_type"])
                else:
                    opt.set(defaults.get("tunnel_type", "local"))
                opt.grid(row=row_idx, column=1, padx=10, pady=5, sticky="w")
                entries[field] = opt
            else:
                ent = ctk.CTkEntry(dialog, width=200)
                ent.grid(row=row_idx, column=1, padx=10, pady=5, sticky="w")
                # 编辑模式只用初始值，添加模式只用默认值
                if is_edit and field in initial_values:
                    ent.insert(0, initial_values[field])
                elif field in defaults:
                    ent.insert(0, defaults[field])
                entries[field] = ent

        def save_tunnel():
            name = entries["name"].get()
            if not name:
                messagebox.showerror("错误", "请输入隧道名称")
                return
            try:
                conf = TunnelConfig(
                    ssh_host=entries["ssh_host"].get(),
                    ssh_port=int(entries["ssh_port"].get()),
                    ssh_user=entries["ssh_user"].get(),
                    ssh_password=entries["ssh_password"].get() or None,
                    ssh_pkey=entries["ssh_pkey"].get() or None,
                    local_bind_port=int(entries["local_bind_port"].get()),
                    remote_bind_host=entries["remote_bind_host"].get(),
                    remote_bind_port=int(entries["remote_bind_port"].get()),
                    autostart=False,
                    tunnel_type=entries["tunnel_type"].get()
                )
                if is_edit:
                    # 如果名称改变了，先删除旧的
                    if edit_name != name and edit_name in config_manager.config.tunnels:
                        config_manager.remove_tunnel(edit_name)
                    else:
                        config_manager.remove_tunnel(edit_name)
                config_manager.add_tunnel(name, conf)
                self.notify_daemon()
                self.add_log(f"隧道 '{name}' {'更新' if is_edit else '添加'}成功", "SUCCESS")
                dialog.destroy()
            except Exception as e:
                self.add_log(f"保存隧道失败：{e}", "ERROR")
                messagebox.showerror("错误", str(e))

        btn_save = ctk.CTkButton(dialog, text="保存", command=save_tunnel)
        btn_save.grid(row=len(fields) + 1, column=0, columnspan=3, pady=20)

    def poll_daemon(self):
        was_offline = False
        while self.running:
            try:
                r = requests.get(f"{DAEMON_URL}/tunnels", timeout=2)
                data = r.json()
                if was_offline:
                    self.add_log("守护进程已连接", "SUCCESS")
                    was_offline = False
                self.status_label.configure(text="守护进程: 在线", text_color="green")
                self.after(0, self.update_tunnels_ui, data)
            except requests.exceptions.ConnectionError:
                if not was_offline:
                    self.add_log("守护进程连接断开", "WARN")
                    was_offline = True
                self.status_label.configure(text="守护进程: 离线", text_color="red")
                # Show local config as unknown
                local_data = {
                    name: {"config": conf.model_dump(), "status": "offline"}
                    for name, conf in config_manager.config.tunnels.items()
                }
                self.after(0, self.update_tunnels_ui, local_data)
            except Exception as e:
                pass
            time.sleep(2)

    def update_tunnels_ui(self, data):
        current_names = set(data.keys())
        displayed_names = set(self.frames.keys())

        # Remove old
        for name in displayed_names - current_names:
            self.frames[name]["frame"].destroy()
            del self.frames[name]

        # Add or update
        for i, name in enumerate(sorted(current_names)):
            info = data[name]
            status = info.get("status", "offline")

            if name not in self.frames:
                frame = ctk.CTkFrame(self.main_frame)
                frame.grid(row=i, column=0, sticky="ew", pady=5, padx=5)
                frame.grid_columnconfigure(1, weight=1)

                lbl_name = ctk.CTkLabel(frame, text=name, font=ctk.CTkFont(weight="bold"))
                lbl_name.grid(row=0, column=0, padx=10, pady=10)

                lbl_desc = ctk.CTkLabel(frame, text="")
                lbl_desc.grid(row=0, column=1, padx=10, pady=10, sticky="w")

                lbl_status = ctk.CTkLabel(frame, text="", width=70)
                lbl_status.grid(row=0, column=2, padx=10, pady=10)

                btn_toggle = ctk.CTkButton(frame, text="启动", width=60)
                btn_toggle.grid(row=0, column=3, padx=5, pady=10)

                btn_edit = ctk.CTkButton(frame, text="编辑", width=50, command=lambda n=name: self.open_add_dialog(n))
                btn_edit.grid(row=0, column=4, padx=5, pady=10)

                btn_delete = ctk.CTkButton(frame, text="删除", width=50, fg_color="red", hover_color="darkred")
                btn_delete.grid(row=0, column=5, padx=5, pady=10)
                btn_delete.configure(command=lambda n=name: self.delete_tunnel(n))

                self.frames[name] = {
                    "frame": frame,
                    "lbl_name": lbl_name,
                    "lbl_desc": lbl_desc,
                    "lbl_status": lbl_status,
                    "btn_toggle": btn_toggle
                }

            # Update content
            ui = self.frames[name]
            ui["frame"].grid(row=i) # Ensure correct order

            conf = info.get("config", {})
            t_type = conf.get("tunnel_type", "local")
            type_label = "反向" if t_type == "remote" else "正向"
            desc = f"{type_label}隧道: 本地: {conf.get('local_bind_port')} -> {conf.get('ssh_host')}:{conf.get('ssh_port')} -> 远端: {conf.get('remote_bind_host')}:{conf.get('remote_bind_port')}"
            ui["lbl_desc"].configure(text=desc)

            if status == "active":
                ui["lbl_status"].configure(text="活跃", text_color="green")
                ui["btn_toggle"].configure(text="停止", command=lambda n=name: self.toggle_tunnel(n, "stop"))
            elif status == "connecting":
                ui["lbl_status"].configure(text="连接中", text_color="orange")
                ui["btn_toggle"].configure(text="停止", command=lambda n=name: self.toggle_tunnel(n, "stop"))
            elif status == "error":
                ui["lbl_status"].configure(text="错误", text_color="red")
                ui["btn_toggle"].configure(text="停止", command=lambda n=name: self.toggle_tunnel(n, "stop"))
            else:
                ui["lbl_status"].configure(text="未连接", text_color="gray")
                ui["btn_toggle"].configure(text="启动", command=lambda n=name: self.toggle_tunnel(n, "start"))

    def toggle_tunnel(self, name, action):
        try:
            r = requests.post(f"{DAEMON_URL}/tunnels/{name}/{action}", timeout=2)
            self.add_log(f"隧道 '{name}' {action}操作已执行", "SUCCESS" if r.status_code == 200 else "ERROR")
        except requests.exceptions.ConnectionError:
            self.add_log(f"无法连接守护进程，隧道 '{name}' {action}失败", "ERROR")
            messagebox.showerror("错误", f"无法{action}隧道：守护进程未运行")
        except Exception as e:
            self.add_log(f"隧道 '{name}' {action}失败：{e}", "ERROR")
            messagebox.showerror("错误", f"无法{action}隧道：{e}")

    def delete_tunnel(self, name):
        if messagebox.askyesno("确认", f"确定要删除隧道 {name} 吗？"):
            config_manager.remove_tunnel(name)
            self.notify_daemon()
            self.add_log(f"隧道 '{name}' 已删除", "INFO")

    def destroy(self):
        self.running = False
        super().destroy()

if __name__ == "__main__":
    app = TunnelApp()
    app.mainloop()
