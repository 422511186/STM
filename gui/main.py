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
from gui.theme import (
    COLORS,
    FONTS,
    RADIUS_LG,
    RADIUS_SM,
    RADIUS_MD,
    CARD_PADDING,
    SIDEBAR_WIDTH,
    SIDEBAR_PADDING,
    sidebar_button_style,
)

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
        x, y, _, _ = (
            self.widget.bbox("insert") if hasattr(self.widget, "bbox") else (0, 0, 0, 0)
        )
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        label = ctk.CTkLabel(
            self.tooltip_window,
            text=self.text,
            font=ctk.CTkFont(size=11),
            fg_color=("gray90", "gray20"),
            text_color=("gray30", "gray70"),
        )
        label.grid(row=0, column=0, padx=5, pady=3)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class TunnelCard(ctk.CTkFrame):
    """可复用的隧道卡片组件"""

    # 状态颜色映射
    STATUS_COLORS = {
        "active": "success",
        "connecting": "warning",
        "error": "error",
        "inactive": "text_muted",
        "offline": "text_muted",
    }

    def __init__(
        self,
        parent,
        name,
        config,
        status,
        on_toggle_callback,
        on_edit_callback,
        on_delete_callback,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        # Store callbacks and state
        self._name = name
        self._config = config
        self._status = status
        self._on_toggle = on_toggle_callback
        self._on_edit = on_edit_callback
        self._on_delete = on_delete_callback

        # Configure card style
        self.configure(
            corner_radius=RADIUS_MD,
            border_width=1,
            border_color=COLORS["border_light"],
            fg_color=COLORS["bg_card"],
        )

        # Grid layout: column0=status indicator, column1=name+desc, column2=buttons
        self.grid_columnconfigure(1, weight=1)

        # === Status Indicator (Left) ===
        self.status_canvas = ctk.CTkCanvas(
            self,
            width=14,
            height=14,
            bd=0,
            highlightthickness=0,
        )
        self.status_canvas.grid(row=0, column=0, padx=(CARD_PADDING, 8), sticky="ns")
        # Draw circle centered in the canvas area
        self.status_dot = self.status_canvas.create_oval(1, 1, 13, 13, fill="#8A8A8A")

        # === Name and Description (Center) ===
        self.lbl_name = ctk.CTkLabel(
            self,
            text=name,
            font=FONTS["heading_sm"],
            text_color=COLORS["text"],
            anchor="w",
        )
        self.lbl_name.grid(
            row=0, column=1, padx=(0, 8), pady=(CARD_PADDING, 4), sticky="w"
        )

        # Build description text
        desc = self._build_description(config)
        self.lbl_desc = ctk.CTkLabel(
            self,
            text=desc,
            font=FONTS["body_sm"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        )
        self.lbl_desc.grid(
            row=1, column=1, padx=(0, 8), pady=(0, CARD_PADDING), sticky="w"
        )

        # === Action Buttons (Right) ===
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(
            row=0, column=2, rowspan=2, padx=(0, CARD_PADDING), pady=0, sticky="e"
        )
        btn_frame.grid_columnconfigure((0, 1, 2), weight=0)

        # Toggle button (Start/Stop)
        self._toggle_action = "start"  # Default action
        self.btn_toggle = ctk.CTkButton(
            btn_frame,
            text="▶ 启动",
            width=80,
            height=32,
            corner_radius=RADIUS_SM,
            font=FONTS["button"],
            command=lambda: self._on_toggle(self._name, self._toggle_action),
        )
        self.btn_toggle.grid(row=0, column=0, padx=(0, 6), pady=0, sticky="e")

        # Edit button
        self.btn_edit = ctk.CTkButton(
            btn_frame,
            text="✏",
            width=36,
            height=32,
            corner_radius=RADIUS_SM,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text"],
            hover_color=COLORS["bg_hover"],
            command=lambda: self._on_edit(self._name),
        )
        self.btn_edit.grid(row=0, column=1, padx=(0, 6), pady=0, sticky="e")

        # Delete button
        self.btn_delete = ctk.CTkButton(
            btn_frame,
            text="🗑",
            width=36,
            height=32,
            corner_radius=RADIUS_SM,
            fg_color=COLORS["error"][0]
            if isinstance(COLORS["error"], tuple)
            else COLORS["error"],
            hover_color=COLORS["error"][1]
            if isinstance(COLORS["error"], tuple)
            else COLORS["error"],
            text_color="white",
            command=lambda: self._on_delete(self._name),
        )
        self.btn_delete.grid(row=0, column=2, padx=0, pady=0, sticky="e")

        # Bind hover effect
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        # Initial status update
        self.set_status(status)

    def _build_description(self, config):
        """Build tunnel description string from config"""
        t_type = config.get("tunnel_type", "local")
        type_label = "反向" if t_type == "remote" else "正向"
        local_port = config.get("local_bind_port", "")
        ssh_host = config.get("ssh_host", "")
        ssh_port = config.get("ssh_port", "")
        remote_host = config.get("remote_bind_host", "")
        remote_port = config.get("remote_bind_port", "")
        return f"{type_label}隧道: 本地:{local_port} → {ssh_host}:{ssh_port} → 远端:{remote_host}:{remote_port}"

    def _on_enter(self, event):
        """Hover enter effect"""
        self.configure(fg_color=COLORS["bg_hover"])

    def _on_leave(self, event):
        """Hover leave effect"""
        self.configure(fg_color=COLORS["bg_card"])

    def _get_status_color(self, status):
        """Get color hex for status indicator"""
        color_key = self.STATUS_COLORS.get(status, "text_muted")
        color = COLORS.get(color_key, COLORS["text_muted"])
        return color[0] if isinstance(color, tuple) else color

    def configure_tunnel(self, name, config, status):
        """Update card content when tunnel config/status changes"""
        self._name = name
        self._config = config
        self._status = status

        self.lbl_name.configure(text=name)
        self.lbl_desc.configure(text=self._build_description(config))
        self.set_status(status)

    def set_status(self, status):
        """Update only the status indicator and button states"""
        self._status = status

        # Update status dot color
        color = self._get_status_color(status)
        self.status_canvas.itemconfig(self.status_dot, fill=color)

        # Determine toggle action based on status
        is_running = status in ("active", "connecting", "error")
        self._toggle_action = "stop" if is_running else "start"

        # Update toggle button based on status
        if status == "active":
            self.btn_toggle.configure(
                text="■ 停止",
                fg_color=COLORS["warning"][0]
                if isinstance(COLORS["warning"], tuple)
                else COLORS["warning"],
                hover_color=COLORS["warning"][1]
                if isinstance(COLORS["warning"], tuple)
                else COLORS["warning"],
                command=lambda: self._on_toggle(self._name, self._toggle_action),
            )
        elif status == "connecting":
            self.btn_toggle.configure(
                text="■ 停止",
                fg_color=COLORS["warning"][0]
                if isinstance(COLORS["warning"], tuple)
                else COLORS["warning"],
                hover_color=COLORS["warning"][1]
                if isinstance(COLORS["warning"], tuple)
                else COLORS["warning"],
                command=lambda: self._on_toggle(self._name, self._toggle_action),
            )
        elif status == "error":
            self.btn_toggle.configure(
                text="■ 停止",
                fg_color=COLORS["error"][0]
                if isinstance(COLORS["error"], tuple)
                else COLORS["error"],
                hover_color=COLORS["error"][1]
                if isinstance(COLORS["error"], tuple)
                else COLORS["error"],
                command=lambda: self._on_toggle(self._name, self._toggle_action),
            )
        else:  # inactive, offline, etc.
            self.btn_toggle.configure(
                text="▶ 启动",
                fg_color=COLORS["success"][0]
                if isinstance(COLORS["success"], tuple)
                else COLORS["success"],
                hover_color=COLORS["success"][1]
                if isinstance(COLORS["success"], tuple)
                else COLORS["success"],
                command=lambda: self._on_toggle(self._name, self._toggle_action),
            )


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
        # Container with rounded corners and sidebar background
        self.sidebar = ctk.CTkFrame(
            self,
            width=SIDEBAR_WIDTH,
            corner_radius=RADIUS_LG,
            fg_color=COLORS["bg_sidebar"],
            border_width=1,
            border_color=COLORS["border_light"],
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 0), pady=(10, 0))
        self.sidebar.grid_rowconfigure(9, weight=1)

        # === Logo Section ===
        # Logo icon (using unicode character for terminal icon)
        self.logo_icon = ctk.CTkLabel(
            self.sidebar, text="🖥️", font=ctk.CTkFont(size=32), width=50, height=50
        )
        self.logo_icon.grid(
            row=0,
            column=0,
            padx=(SIDEBAR_PADDING, 0),
            pady=(SIDEBAR_PADDING, 0),
            sticky="w",
        )

        # Logo text
        self.logo_label = ctk.CTkLabel(
            self.sidebar,
            text="SSH 隧道管理器",
            font=FONTS["heading"],
            text_color=COLORS["sidebar_text"],
            anchor="w",
        )
        self.logo_label.grid(
            row=0,
            column=1,
            padx=(8, SIDEBAR_PADDING),
            pady=(SIDEBAR_PADDING, 0),
            sticky="w",
        )

        # Separator line under logo
        self.separator_top = ctk.CTkFrame(
            self.sidebar, height=1, fg_color=COLORS["border_light"]
        )
        self.separator_top.grid(
            row=1,
            column=0,
            columnspan=2,
            padx=SIDEBAR_PADDING,
            pady=(SIDEBAR_PADDING, 12),
            sticky="ew",
        )

        # === Daemon Control Section ===
        self.section_daemon = ctk.CTkLabel(
            self.sidebar,
            text="守护进程",
            font=FONTS["body_sm"],
            text_color=COLORS["sidebar_text_muted"],
            anchor="w",
        )
        self.section_daemon.grid(
            row=2, column=0, columnspan=2, padx=SIDEBAR_PADDING, pady=(0, 6), sticky="w"
        )

        self.btn_start_daemon = ctk.CTkButton(
            self.sidebar,
            text="▶  启动守护进程",
            command=self.start_daemon,
            **sidebar_button_style(),
        )
        self.btn_start_daemon.grid(
            row=3,
            column=0,
            columnspan=2,
            padx=SIDEBAR_PADDING,
            pady=(0, 6),
            sticky="ew",
        )

        self.btn_stop_daemon = ctk.CTkButton(
            self.sidebar,
            text="■  关闭守护进程",
            command=self.stop_daemon,
            fg_color=COLORS["error"][0]
            if isinstance(COLORS["error"], tuple)
            else COLORS["error"],
            hover_color=COLORS["error"][1]
            if isinstance(COLORS["error"], tuple)
            else COLORS["error"],
            text_color="white",
            corner_radius=RADIUS_SM,
            height=42,
        )
        self.btn_stop_daemon.grid(
            row=4,
            column=0,
            columnspan=2,
            padx=SIDEBAR_PADDING,
            pady=(0, 6),
            sticky="ew",
        )

        # === Tunnel Management Section ===
        self.separator_mid = ctk.CTkFrame(
            self.sidebar, height=1, fg_color=COLORS["border_light"]
        )
        self.separator_mid.grid(
            row=5,
            column=0,
            columnspan=2,
            padx=SIDEBAR_PADDING,
            pady=(12, 0),
            sticky="ew",
        )

        self.section_tunnel = ctk.CTkLabel(
            self.sidebar,
            text="隧道管理",
            font=FONTS["body_sm"],
            text_color=COLORS["sidebar_text_muted"],
            anchor="w",
        )
        self.section_tunnel.grid(
            row=6,
            column=0,
            columnspan=2,
            padx=SIDEBAR_PADDING,
            pady=(12, 6),
            sticky="w",
        )

        self.btn_add = ctk.CTkButton(
            self.sidebar,
            text="➕  添加隧道",
            command=self.open_add_dialog,
            **sidebar_button_style(),
        )
        self.btn_add.grid(
            row=7,
            column=0,
            columnspan=2,
            padx=SIDEBAR_PADDING,
            pady=(0, 6),
            sticky="ew",
        )

        self.btn_import = ctk.CTkButton(
            self.sidebar,
            text="📥  导入配置",
            command=self.import_config,
            **sidebar_button_style(),
        )
        self.btn_import.grid(
            row=8,
            column=0,
            columnspan=2,
            padx=SIDEBAR_PADDING,
            pady=(0, 6),
            sticky="ew",
        )

        self.btn_export = ctk.CTkButton(
            self.sidebar,
            text="📤  导出配置",
            command=self.export_config,
            **sidebar_button_style(),
        )
        self.btn_export.grid(
            row=9,
            column=0,
            columnspan=2,
            padx=SIDEBAR_PADDING,
            pady=(0, 6),
            sticky="ew",
        )

        # === Status Indicator (at bottom) ===
        self.status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_frame.grid(
            row=10,
            column=0,
            columnspan=2,
            padx=SIDEBAR_PADDING,
            pady=(12, SIDEBAR_PADDING),
            sticky="ew",
        )
        self.status_frame.grid_columnconfigure(0, weight=0)
        self.status_frame.grid_columnconfigure(1, weight=1)

        # Status indicator dot (using canvas for better control)
        self.status_canvas = ctk.CTkCanvas(
            self.status_frame,
            width=10,
            height=10,
            bd=0,
            highlightthickness=0,
            bg=ctk.ThemeManager.theme["CTkFrame"]["fg_color"][0]
            if hasattr(ctk, "ThemeManager")
            else "#FFFFFF",
        )
        self.status_canvas.grid(row=0, column=0, padx=(0, 8), sticky="w")
        self.status_dot = self.status_canvas.create_oval(0, 0, 10, 10, fill="#E6A700")

        # Status text label
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="守护进程: 检查中...",
            font=FONTS["body_sm"],
            text_color=COLORS["warning"][0]
            if isinstance(COLORS["warning"], tuple)
            else COLORS["warning"],
            anchor="w",
        )
        self.status_label.grid(row=0, column=1, sticky="w")

    def _build_log_area(self):
        self.log_frame = ctk.CTkFrame(
            self,
            corner_radius=RADIUS_SM,
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["border_light"],
        )
        self.log_frame.grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 10)
        )
        self.log_frame.grid_propagate(False)
        self.log_frame.grid_rowconfigure(1, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)

        self.log_title = ctk.CTkLabel(
            self.log_frame,
            text="📋 操作日志",
            font=FONTS["heading_sm"],
        )
        self.log_title.grid(row=0, column=0, padx=15, pady=(12, 8), sticky="w")

        self.log_text = ctk.CTkTextbox(
            self.log_frame,
            font=FONTS["mono"],
            fg_color=COLORS["bg_card"],
            border_width=0,
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 12))
        self.log_text.configure(state="disabled")

        # Configure text tags for colored log levels
        self._setup_log_tags()

    def _setup_log_tags(self):
        """Setup text tags for colored log display"""
        # INFO - blue
        self.log_text.tag_config("INFO", foreground=COLORS["info"][0])
        # SUCCESS - green
        self.log_text.tag_config("SUCCESS", foreground=COLORS["success"][0])
        # ERROR - red
        self.log_text.tag_config("ERROR", foreground=COLORS["error"][0])
        # WARN - orange
        self.log_text.tag_config("WARN", foreground=COLORS["warning"][0])
        # Timestamp - muted
        self.log_text.tag_config("TIMESTAMP", foreground=COLORS["text_muted"][0])

    def _is_dark_mode(self) -> bool:
        """Check if dark mode is active"""
        return ctk.get_appearance_mode().lower() == "dark"

    def _get_log_color(self, level: str) -> str:
        """Get color for log level"""
        colors = {
            "INFO": COLORS["info"],
            "SUCCESS": COLORS["success"],
            "ERROR": COLORS["error"],
            "WARN": COLORS["warning"],
        }
        return colors.get(level, COLORS["info"])[0]

    def add_log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = self._get_log_color(level)

        self.log_lines.append(
            {"timestamp": timestamp, "level": level, "message": message}
        )
        if len(self.log_lines) > self.max_log_lines:
            self.log_lines.pop(0)

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")

        for line in self.log_lines:
            ts = line["timestamp"]
            lvl = line["level"]
            msg = line["message"]

            # Insert timestamp with muted color
            self.log_text.insert("end", f"[{ts}] ", "TIMESTAMP")
            # Insert level with appropriate color
            self.log_text.insert("end", f"[{lvl}] ", lvl)
            # Insert message
            self.log_text.insert("end", f"{msg}\n", None)

        self.log_text.configure(state="disabled")

    def _build_main_area(self):
        # Main area container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Header with title and quick add button
        self.main_header = ctk.CTkFrame(
            self.main_container,
            fg_color="transparent",
        )
        self.main_header.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 16))
        self.main_header.grid_columnconfigure(0, weight=1)
        self.main_header.grid_columnconfigure(1, weight=0)

        # Title
        self.main_title = ctk.CTkLabel(
            self.main_header,
            text="🔒 我的隧道",
            font=FONTS["heading"],
            text_color=COLORS["text"],
            anchor="w",
        )
        self.main_title.grid(row=0, column=0, sticky="w")

        # Quick add button (same style as sidebar add button)
        self.btn_add_quick = ctk.CTkButton(
            self.main_header,
            text="➕ 添加",
            command=self.open_add_dialog,
            width=90,
            height=32,
            corner_radius=RADIUS_SM,
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
        )
        self.btn_add_quick.grid(row=0, column=1, sticky="e")

        # Tunnel count label
        self.tunnel_count_label = ctk.CTkLabel(
            self.main_header,
            text="",
            font=FONTS["body_sm"],
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.tunnel_count_label.grid(
            row=1, column=0, columnspan=2, sticky="w", padx=(4, 0), pady=(4, 0)
        )

        # Scrollable frame for tunnel cards
        self.main_frame = ctk.CTkScrollableFrame(
            self.main_container,
            corner_radius=RADIUS_MD,
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["border_light"],
        )
        self.main_frame.grid(row=1, column=0, sticky="nsew", pady=0)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Empty state placeholder (shown when no tunnels) - overlay on main_frame
        self.empty_state = ctk.CTkFrame(
            self.main_container,
            corner_radius=RADIUS_MD,
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["border_light"],
        )
        self.empty_state.grid(row=1, column=0, sticky="nsew")
        self.empty_state.grid_columnconfigure(0, weight=1)

        self.empty_icon = ctk.CTkLabel(
            self.empty_state,
            text="📡",
            font=ctk.CTkFont(size=48),
            text_color=COLORS["text_muted"],
        )
        self.empty_icon.grid(row=0, column=0, pady=(60, 16))

        self.empty_title = ctk.CTkLabel(
            self.empty_state,
            text="还没有隧道",
            font=FONTS["heading_sm"],
            text_color=COLORS["text_secondary"],
        )
        self.empty_title.grid(row=1, column=0, pady=(0, 8))

        self.empty_desc = ctk.CTkLabel(
            self.empty_state,
            text="点击「添加隧道」来创建你的第一个 SSH 隧道",
            font=FONTS["body_sm"],
            text_color=COLORS["text_muted"],
        )
        self.empty_desc.grid(row=2, column=0, pady=(0, 24))

        self.empty_btn = ctk.CTkButton(
            self.empty_state,
            text="➕ 添加隧道",
            command=self.open_add_dialog,
            width=140,
            height=36,
            corner_radius=RADIUS_SM,
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
        )
        self.empty_btn.grid(row=3, column=0, pady=(0, 60))

        # Initially show empty state (will be hidden/shown by update_tunnels_ui)
        self.empty_state.grid(row=1, column=0, sticky="nsew")
        self.main_frame.grid_remove()  # Hide tunnel list initially

    def start_daemon(self):
        self.add_log("正在启动守护进程...", "INFO")
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
        self.add_log("守护进程启动命令已发送", "INFO")
        messagebox.showinfo("守护进程", "守护进程已在后台启动。")

    def stop_daemon(self):
        try:
            r = requests.post(f"{DAEMON_URL}/shutdown", timeout=3)
            self.add_log("关闭守护进程请求已发送", "INFO")
            error_color = (
                COLORS["error"][0]
                if isinstance(COLORS["error"], tuple)
                else COLORS["error"]
            )
            self.update_status_indicator("守护进程: 离线", error_color)
            messagebox.showinfo("守护进程", "守护进程关闭请求已发送。")
        except requests.exceptions.ConnectionError:
            self.add_log("守护进程未运行", "WARN")
            messagebox.showinfo("守护进程", "守护进程未运行。")
        except Exception as e:
            self.add_log(f"关闭守护进程失败：{e}", "ERROR")
            messagebox.showerror("错误", f"关闭守护进程失败：{e}")

    def import_config(self):
        path = filedialog.askopenfilename(
            filetypes=[("YAML 文件", "*.yaml"), ("所有文件", "*.*")]
        )
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
        path = filedialog.asksaveasfilename(
            defaultextension=".yaml", filetypes=[("YAML 文件", "*.yaml")]
        )
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
        """打开添加/编辑隧道对话框"""
        dialog = ctk.CTkToplevel(self)
        is_edit = edit_name is not None
        dialog.title("✏️ 编辑隧道" if is_edit else "➕ 添加隧道")
        dialog.configure(fg_color=COLORS["bg_card"])
        dialog.resizable(False, False)

        # 让对话框居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (520 // 2)
        y = (dialog.winfo_screenheight() // 2) - (900 // 2)
        dialog.geometry(f"520x900+{x}+{y}")

        # 确保对话框置顶
        dialog.transient(self)  # 设为临时窗口
        dialog.grab_set()  # 捕获所有事件，成为模态窗口
        dialog.lift()  # 提升到最前面

        # 字段配置数据
        FIELD_DEFS = [
            # 分组1: 基础信息
            {
                "section": "基础信息",
                "fields": [
                    {"key": "name", "label": "名称", "placeholder": "隧道的唯一标识"},
                ],
            },
            # 分组2: SSH连接
            {
                "section": "SSH 连接",
                "fields": [
                    {
                        "key": "tunnel_type",
                        "label": "隧道类型",
                        "type": "option",
                        "values": ["local", "remote"],
                    },
                    {
                        "key": "ssh_host",
                        "label": "SSH 主机",
                        "placeholder": "SSH服务器地址",
                    },
                    {"key": "ssh_port", "label": "SSH 端口", "placeholder": "22"},
                    {"key": "ssh_user", "label": "SSH 用户", "placeholder": "用户名"},
                    {
                        "key": "ssh_password",
                        "label": "SSH 密码",
                        "placeholder": "留空使用私钥",
                    },
                    {
                        "key": "ssh_pkey",
                        "label": "私钥路径",
                        "placeholder": "~/.ssh/id_rsa",
                    },
                ],
            },
            # 分组3: 隧道设置
            {
                "section": "隧道设置",
                "fields": [
                    {
                        "key": "local_bind_port",
                        "label": "本地端口",
                        "placeholder": "本机监听端口",
                    },
                    {
                        "key": "remote_bind_host",
                        "label": "远端主机",
                        "placeholder": "127.0.0.1",
                    },
                    {
                        "key": "remote_bind_port",
                        "label": "远端端口",
                        "placeholder": "目标端口",
                    },
                ],
            },
        ]

        DEFAULTS = {
            "ssh_port": "22",
            "tunnel_type": "local",
            "remote_bind_host": "127.0.0.1",
        }

        FIELD_HINTS = {
            "name": "隧道的唯一标识名称",
            "tunnel_type": "local=正向(访问远程), remote=反向(暴露本地)",
            "ssh_host": "SSH服务器地址（IP或域名）",
            "ssh_port": "SSH服务端口，默认22",
            "ssh_user": "SSH登录用户名",
            "ssh_password": "密码认证（推荐使用私钥）",
            "ssh_pkey": "私钥文件路径，如 ~/.ssh/id_rsa",
            "local_bind_port": "正向:本机监听端口 | 反向:本机服务端口",
            "remote_bind_host": "正向:远端目标主机 | 反向:通常127.0.0.1",
            "remote_bind_port": "正向:远端目标端口 | 反向:SSH服务器监听端口",
        }

        HELP_TEXTS = {
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

前提: SSH服务器需开启 GatewayPorts""",
        }

        entries = {}

        # ========== 标题 ==========
        title_label = ctk.CTkLabel(
            dialog,
            text="✏️ 编辑隧道" if is_edit else "➕ 添加隧道",
            font=FONTS["heading_sm"],
            text_color=COLORS["text"],
        )
        title_label.grid(
            row=0, column=0, columnspan=2, padx=20, pady=(20, 8), sticky="w"
        )

        # ========== 帮助说明框 ==========
        help_frame = ctk.CTkFrame(
            dialog,
            fg_color=COLORS["bg_input"],
            corner_radius=RADIUS_SM,
            border_width=1,
            border_color=COLORS["border_light"],
        )
        help_frame.grid(
            row=1, column=0, columnspan=2, padx=20, pady=(0, 12), sticky="ew"
        )
        help_frame.grid_columnconfigure(0, weight=1)

        help_label = ctk.CTkLabel(
            help_frame,
            text=HELP_TEXTS["local"],
            font=FONTS["body_sm"],
            justify="left",
            text_color=COLORS["text_secondary"],
        )
        help_label.grid(row=0, column=0, padx=12, pady=10, sticky="w")

        def update_help_text(choice):
            help_label.configure(text=HELP_TEXTS.get(choice, HELP_TEXTS["local"]))

        # ========== 预填值（编辑模式） ==========
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
                "remote_bind_port": str(t.remote_bind_port),
            }
            help_label.configure(
                text=HELP_TEXTS.get(t.tunnel_type, HELP_TEXTS["local"])
            )

        # ========== 构建表单 ==========
        current_row = 2

        for group in FIELD_DEFS:
            # 分组标题
            section_label = ctk.CTkLabel(
                dialog,
                text=group["section"],
                font=FONTS["body_sm"],
                text_color=COLORS["text_muted"],
            )
            section_label.grid(
                row=current_row,
                column=0,
                columnspan=2,
                padx=20,
                pady=(8, 4),
                sticky="w",
            )
            current_row += 1

            # 创建分组内的字段
            for field_def in group["fields"]:
                field_key = field_def["key"]
                field_label = field_def["label"]

                # Label
                lbl = ctk.CTkLabel(
                    dialog,
                    text=field_label,
                    font=FONTS["label"],
                    text_color=COLORS["text"],
                    width=100,
                    anchor="e",
                )
                lbl.grid(row=current_row, column=0, padx=(20, 8), pady=4, sticky="e")

                # 输入控件
                if field_def.get("type") == "option":
                    opt = ctk.CTkOptionMenu(
                        dialog,
                        values=field_def["values"],
                        width=250,
                        height=32,
                        corner_radius=RADIUS_SM,
                        font=FONTS["body"],
                        command=update_help_text,
                    )
                    if is_edit and "tunnel_type" in initial_values:
                        opt.set(initial_values["tunnel_type"])
                    else:
                        opt.set(DEFAULTS.get("tunnel_type", "local"))
                    opt.grid(
                        row=current_row, column=1, padx=(0, 20), pady=4, sticky="w"
                    )
                    entries[field_key] = opt
                else:
                    ent = ctk.CTkEntry(
                        dialog,
                        width=250,
                        height=32,
                        corner_radius=RADIUS_SM,
                        border_width=1,
                        fg_color=COLORS["bg_input"],
                        text_color=COLORS["text"],
                        placeholder_text_color=COLORS["text_muted"],
                        font=FONTS["body"],
                    )
                    if field_def.get("placeholder"):
                        ent.configure(placeholder_text=field_def["placeholder"])

                    if is_edit and field_key in initial_values:
                        ent.insert(0, initial_values[field_key])
                    elif field_key in DEFAULTS:
                        ent.insert(0, DEFAULTS[field_key])
                    ent.grid(
                        row=current_row, column=1, padx=(0, 20), pady=4, sticky="w"
                    )
                    entries[field_key] = ent

                    # Tooltip hint
                    if field_key in FIELD_HINTS:
                        hint = ctk.CTkLabel(
                            dialog,
                            text="?",
                            width=20,
                            text_color=COLORS["text_muted"],
                            cursor="question_arrow",
                        )
                        hint.grid(
                            row=current_row, column=1, padx=(0, 5), pady=4, sticky="e"
                        )
                        ToolTip(hint, FIELD_HINTS[field_key])

                current_row += 1

            # 分组分隔线
            if group != FIELD_DEFS[-1]:
                sep = ctk.CTkFrame(
                    dialog,
                    height=1,
                    fg_color=COLORS["border_light"],
                )
                sep.grid(
                    row=current_row,
                    column=0,
                    columnspan=2,
                    padx=20,
                    pady=(8, 0),
                    sticky="ew",
                )
                current_row += 1

        # ========== 按钮区域 ==========
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.grid(row=current_row, column=0, columnspan=2, pady=20)

        # 保存逻辑（需要在按钮之前定义）
        def _save_tunnel_from_dialog():
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
                    tunnel_type=entries["tunnel_type"].get(),
                )
                if is_edit:
                    if edit_name != name and edit_name in config_manager.config.tunnels:
                        config_manager.remove_tunnel(edit_name)
                    else:
                        config_manager.remove_tunnel(edit_name)
                config_manager.add_tunnel(name, conf)
                self.notify_daemon()
                self.add_log(
                    f"隧道 '{name}' {'更新' if is_edit else '添加'}成功", "SUCCESS"
                )
                dialog.destroy()
            except Exception as e:
                self.add_log(f"保存隧道失败：{e}", "ERROR")
                messagebox.showerror("错误", str(e))

        # 根据当前主题模式获取颜色
        is_dark = ctk.get_appearance_mode().lower() == "dark"
        border_color = COLORS["border"][1] if is_dark else COLORS["border"][0]
        text_color = COLORS["text"][1] if is_dark else COLORS["text"][0]
        bg_hover = COLORS["bg_hover"][1] if is_dark else COLORS["bg_hover"][0]

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="取消",
            width=120,
            height=36,
            corner_radius=RADIUS_SM,
            font=FONTS["button"],
            fg_color="transparent",
            border_width=1,
            border_color=border_color,
            text_color=text_color,
            hover_color=bg_hover,
            command=dialog.destroy,
        )
        btn_cancel.grid(row=0, column=0, padx=(0, 12))

        btn_save = ctk.CTkButton(
            btn_frame,
            text="保存",
            width=120,
            height=36,
            corner_radius=RADIUS_SM,
            font=FONTS["button"],
            fg_color=COLORS["primary"][1] if is_dark else COLORS["primary"][0],
            hover_color=COLORS["primary_hover"][1] if is_dark else COLORS["primary_hover"][0],
            text_color="white",
            command=_save_tunnel_from_dialog,
        )
        btn_save.grid(row=0, column=1, padx=0)

        # 支持按回车键保存
        dialog.bind("<Return>", lambda e: _save_tunnel_from_dialog())

    def update_status_indicator(self, text, color_hex):
        """Update status label and indicator dot color"""
        self.status_label.configure(text=text)
        # Update canvas dot color
        self.status_canvas.itemconfig(self.status_dot, fill=color_hex)

    def poll_daemon(self):
        was_offline = False
        while self.running:
            try:
                r = requests.get(f"{DAEMON_URL}/tunnels", timeout=2)
                data = r.json()
                if was_offline:
                    self.add_log("守护进程已连接", "SUCCESS")
                    was_offline = False
                success_color = (
                    COLORS["success"][0]
                    if isinstance(COLORS["success"], tuple)
                    else COLORS["success"]
                )
                self.after(
                    0, self.update_status_indicator, "守护进程: 在线", success_color
                )
                self.after(0, self.update_tunnels_ui, data)
            except requests.exceptions.ConnectionError:
                if not was_offline:
                    self.add_log("守护进程连接断开", "WARN")
                    was_offline = True
                error_color = (
                    COLORS["error"][0]
                    if isinstance(COLORS["error"], tuple)
                    else COLORS["error"]
                )
                self.after(
                    0, self.update_status_indicator, "守护进程: 离线", error_color
                )
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

        # Show/hide empty state based on tunnel count
        if len(current_names) == 0:
            # No tunnels - show empty state
            self.empty_state.grid(row=1, column=0, sticky="nsew")
            self.empty_state.lift()  # Bring to front
            self.main_frame.grid_remove()
            self.tunnel_count_label.configure(text="")
        else:
            # Has tunnels - show main frame, hide empty state
            self.main_frame.grid(row=1, column=0, sticky="nsew")
            self.main_frame.lift()  # Bring to front
            self.empty_state.grid_remove()

            # Update tunnel count
            active_count = sum(
                1 for info in data.values() if info.get("status") == "active"
            )
            total_count = len(current_names)
            if active_count > 0:
                self.tunnel_count_label.configure(
                    text=f"共 {total_count} 个隧道，{active_count} 个活跃"
                )
            else:
                self.tunnel_count_label.configure(text=f"共 {total_count} 个隧道")

        # Remove old
        for name in displayed_names - current_names:
            self.frames[name].destroy()
            del self.frames[name]

        # Add or update
        for i, name in enumerate(sorted(current_names)):
            info = data[name]
            config = info.get("config", {})
            status = info.get("status", "offline")

            if name not in self.frames:
                # Create new TunnelCard
                card = TunnelCard(
                    self.main_frame,
                    name=name,
                    config=config,
                    status=status,
                    on_toggle_callback=self.toggle_tunnel,
                    on_edit_callback=self.open_add_dialog,
                    on_delete_callback=self.delete_tunnel,
                )
                card.grid(row=i, column=0, sticky="ew", pady=5, padx=5)
                self.frames[name] = card
            else:
                # Update existing card
                card = self.frames[name]
                card.grid(row=i)  # Ensure correct order
                card.configure_tunnel(name, config, status)

    def toggle_tunnel(self, name, action):
        try:
            r = requests.post(f"{DAEMON_URL}/tunnels/{name}/{action}", timeout=2)
            self.add_log(
                f"隧道 '{name}' {action}操作已执行",
                "SUCCESS" if r.status_code == 200 else "ERROR",
            )
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
