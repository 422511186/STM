import ctypes
import sys
import os

if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

import customtkinter as ctk
import requests
import threading
import time
from tkinter import messagebox, filedialog
from core.config import config_manager, TunnelConfig
import subprocess
from datetime import datetime
from gui.theme import (
    COLORS,
    FONTS,
    RADIUS_SM,
    RADIUS_MD,
    CARD_PADDING,
    SIDEBAR_WIDTH,
    SIDEBAR_PADDING,
    sidebar_button_style,
    _c,
)

DAEMON_URL = f"http://{os.environ.get('SSH_TUNNEL_MANAGER_HOST', '127.0.0.1')}:{os.environ.get('SSH_TUNNEL_MANAGER_PORT', '50051')}"

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class TunnelCard(ctk.CTkFrame):
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

        self._name = name
        self._config = config
        self._status = status
        self._on_toggle = on_toggle_callback
        self._on_edit = on_edit_callback
        self._on_delete = on_delete_callback
        self._bg_color = self._get_bg_color()

        self.configure(
            corner_radius=RADIUS_MD,
            border_width=1,
            border_color=COLORS["border_light"],
            fg_color=COLORS["bg_card"],
        )

        self.grid_columnconfigure(0, weight=0, minsize=32)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        # Status dot using a simple frame instead of canvas
        self.status_frame = ctk.CTkFrame(
            self,
            width=10,
            height=10,
            corner_radius=5,
            fg_color="#9CA3AF",
        )
        self.status_frame.grid(
            row=0, column=0, rowspan=2, padx=(CARD_PADDING, 10), pady=CARD_PADDING, sticky="ns"
        )
        self.status_frame.grid_propagate(False)

        self.lbl_name = ctk.CTkLabel(
            self,
            text=name,
            font=FONTS["heading_sm"],
            text_color=COLORS["text"],
            anchor="w",
        )
        self.lbl_name.grid(
            row=0, column=1, padx=(0, 8), pady=(CARD_PADDING - 2, 2), sticky="w"
        )

        desc = self._build_description(config)
        self.lbl_desc = ctk.CTkLabel(
            self,
            text=desc,
            font=FONTS["body_sm"],
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.lbl_desc.grid(
            row=1, column=1, padx=(0, 8), pady=(0, CARD_PADDING - 2), sticky="w"
        )

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(
            row=0, column=2, rowspan=2, padx=(0, CARD_PADDING), pady=CARD_PADDING, sticky="e"
        )

        self._toggle_action = "start"
        self.btn_toggle = ctk.CTkButton(
            btn_frame,
            text="\u542f\u52a8",
            width=56,
            height=28,
            corner_radius=RADIUS_SM,
            font=FONTS["button"],
            fg_color=COLORS["success"],
            hover_color=COLORS["success_hover"],
            text_color="white",
            command=lambda: self._on_toggle(self._name, self._toggle_action),
        )
        self.btn_toggle.grid(row=0, column=0, padx=(0, 6))

        self.btn_edit = ctk.CTkButton(
            btn_frame,
            text="\u7f16\u8f91",
            width=40,
            height=28,
            corner_radius=RADIUS_SM,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_muted"],
            hover_color=COLORS["bg_hover"],
            font=FONTS["button"],
            command=lambda: self._on_edit(self._name),
        )
        self.btn_edit.grid(row=0, column=1, padx=(0, 6))

        self.btn_delete = ctk.CTkButton(
            btn_frame,
            text="\u5220\u9664",
            width=40,
            height=28,
            corner_radius=RADIUS_SM,
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["error"],
            hover_color=COLORS["error_subtle"],
            font=FONTS["button"],
            command=lambda: self._on_delete(self._name),
        )
        self.btn_delete.grid(row=0, column=2)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Configure>", self._on_resize)

        self.set_status(status)

    def _get_bg_color(self):
        is_dark = ctk.get_appearance_mode().lower() == "dark"
        return COLORS["bg_card"][1] if is_dark else COLORS["bg_card"][0]

    def _build_description(self, config):
        t_type = config.get("tunnel_type", "local")
        type_label = "\u53cd\u5411" if t_type == "remote" else "\u6b63\u5411"
        local_port = config.get("local_bind_port", "")
        ssh_host = config.get("ssh_host", "")
        ssh_port = config.get("ssh_port", "")
        remote_host = config.get("remote_bind_host", "")
        remote_port = config.get("remote_bind_port", "")
        return f"{type_label}  {local_port} -> {ssh_host}:{ssh_port} -> {remote_host}:{remote_port}"

    def _on_enter(self, event):
        self.configure(fg_color=COLORS["bg_hover"])

    def _on_leave(self, event):
        self.configure(fg_color=COLORS["bg_card"])

    def _on_resize(self, event):
        self._bg_color = self._get_bg_color()

    def _get_status_color(self, status):
        color_key = self.STATUS_COLORS.get(status, "text_muted")
        color = COLORS.get(color_key, COLORS["text_muted"])
        return color[0] if isinstance(color, tuple) else color

    def configure_tunnel(self, name, config, status):
        self._name = name
        self._config = config
        self._status = status
        self.lbl_name.configure(text=name)
        self.lbl_desc.configure(text=self._build_description(config))
        self.set_status(status)

    def set_status(self, status):
        self._status = status
        color = self._get_status_color(status)
        self.status_frame.configure(fg_color=color)

        is_running = status in ("active", "connecting", "error")
        self._toggle_action = "stop" if is_running else "start"

        if status == "active":
            self.btn_toggle.configure(
                text="\u505c\u6b62",
                fg_color=COLORS["warning"],
                hover_color=COLORS["warning_hover"],
                text_color="white",
                command=lambda: self._on_toggle(self._name, self._toggle_action),
            )
        elif status == "connecting":
            self.btn_toggle.configure(
                text="\u505c\u6b62",
                fg_color=COLORS["warning"],
                hover_color=COLORS["warning_hover"],
                text_color="white",
                command=lambda: self._on_toggle(self._name, self._toggle_action),
            )
        elif status == "error":
            self.btn_toggle.configure(
                text="\u505c\u6b62",
                fg_color=COLORS["error"],
                hover_color=COLORS["error_hover"],
                text_color="white",
                command=lambda: self._on_toggle(self._name, self._toggle_action),
            )
        else:
            self.btn_toggle.configure(
                text="\u542f\u52a8",
                fg_color=COLORS["success"],
                hover_color=COLORS["success_hover"],
                text_color="white",
                command=lambda: self._on_toggle(self._name, self._toggle_action),
            )


class TunnelApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SSH \u96a7\u9053\u7ba1\u7406\u5668")
        self.geometry("1020x680")
        self.configure(fg_color=COLORS["bg_main"])

        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.tunnels_data = {}
        self.frames = {}
        self.log_lines = []
        self.max_log_lines = 100

        self._build_sidebar()
        self._build_main_area()
        self._build_log_area()

        self.running = True
        threading.Thread(target=self.poll_daemon, daemon=True).start()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self,
            width=SIDEBAR_WIDTH,
            corner_radius=0,
            fg_color=COLORS["bg_sidebar"],
            border_width=0,
        )
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)

        for i in range(13):
            self.sidebar.grid_rowconfigure(i, weight=0)
        self.sidebar.grid_rowconfigure(10, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=SIDEBAR_PADDING, pady=(SIDEBAR_PADDING, 0), sticky="ew")
        logo_frame.grid_columnconfigure(1, weight=1)

        self.logo_icon = ctk.CTkLabel(
            logo_frame,
            text="\u26a1",
            font=ctk.CTkFont(size=18, weight="bold"),
            width=24,
            height=24,
        )
        self.logo_icon.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.logo_label = ctk.CTkLabel(
            logo_frame,
            text="SSH \u96a7\u9053",
            font=FONTS["heading_sm"],
            text_color=COLORS["sidebar_text"],
            anchor="w",
        )
        self.logo_label.grid(row=0, column=1, sticky="w")

        self.separator_top = ctk.CTkFrame(
            self.sidebar, height=1, fg_color=COLORS["border_light"]
        )
        self.separator_top.grid(
            row=1, column=0, padx=SIDEBAR_PADDING, pady=(16, 16), sticky="ew"
        )

        self.section_daemon = ctk.CTkLabel(
            self.sidebar,
            text="\u5b88\u62a4\u8fdb\u7a0b",
            font=FONTS["body_sm"],
            text_color=COLORS["sidebar_text_muted"],
            anchor="w",
        )
        self.section_daemon.grid(
            row=2, column=0, padx=SIDEBAR_PADDING, pady=(0, 8), sticky="w"
        )

        self.btn_start_daemon = ctk.CTkButton(
            self.sidebar,
            text="  \u542f\u52a8\u5b88\u62a4\u8fdb\u7a0b",
            command=self.start_daemon,
            **sidebar_button_style(),
        )
        self.btn_start_daemon.grid(
            row=3, column=0, padx=SIDEBAR_PADDING, pady=(0, 6), sticky="ew"
        )

        self.btn_stop_daemon = ctk.CTkButton(
            self.sidebar,
            text="  \u5173\u95ed\u5b88\u62a4\u8fdb\u7a0b",
            command=self.stop_daemon,
            **sidebar_button_style(),
        )
        self.btn_stop_daemon.grid(
            row=4, column=0, padx=SIDEBAR_PADDING, pady=(0, 6), sticky="ew"
        )

        self.separator_mid = ctk.CTkFrame(
            self.sidebar, height=1, fg_color=COLORS["border_light"]
        )
        self.separator_mid.grid(
            row=5, column=0, padx=SIDEBAR_PADDING, pady=(16, 0), sticky="ew"
        )

        self.section_tunnel = ctk.CTkLabel(
            self.sidebar,
            text="\u96a7\u9053\u7ba1\u7406",
            font=FONTS["body_sm"],
            text_color=COLORS["sidebar_text_muted"],
            anchor="w",
        )
        self.section_tunnel.grid(
            row=6, column=0, padx=SIDEBAR_PADDING, pady=(16, 8), sticky="w"
        )

        self.btn_add = ctk.CTkButton(
            self.sidebar,
            text="  \u6dfb\u52a0\u96a7\u9053",
            command=self.open_add_dialog,
            **sidebar_button_style(),
        )
        self.btn_add.grid(
            row=7, column=0, padx=SIDEBAR_PADDING, pady=(0, 6), sticky="ew"
        )

        self.btn_import = ctk.CTkButton(
            self.sidebar,
            text="  \u5bfc\u5165\u914d\u7f6e",
            command=self.import_config,
            **sidebar_button_style(),
        )
        self.btn_import.grid(
            row=8, column=0, padx=SIDEBAR_PADDING, pady=(0, 6), sticky="ew"
        )

        self.btn_export = ctk.CTkButton(
            self.sidebar,
            text="  \u5bfc\u51fa\u914d\u7f6e",
            command=self.export_config,
            **sidebar_button_style(),
        )
        self.btn_export.grid(
            row=9, column=0, padx=SIDEBAR_PADDING, pady=(0, 6), sticky="ew"
        )

        self.separator_bottom = ctk.CTkFrame(
            self.sidebar, height=1, fg_color=COLORS["border_light"]
        )
        self.separator_bottom.grid(
            row=10, column=0, padx=SIDEBAR_PADDING, pady=(16, 0), sticky="ew"
        )

        self.status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.status_frame.grid(
            row=11, column=0, padx=SIDEBAR_PADDING, pady=(12, SIDEBAR_PADDING - 4), sticky="ew"
        )
        self.status_frame.grid_columnconfigure(1, weight=1)

        self.status_dot = ctk.CTkFrame(
            self.status_frame,
            width=8,
            height=8,
            corner_radius=4,
            fg_color="#F59E0B",
        )
        self.status_dot.grid(row=0, column=0, padx=(0, 8), sticky="w")
        self.status_dot.grid_propagate(False)

        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="\u5b88\u62a4\u8fdb\u7a0b: \u68c0\u67e5\u4e2d...",
            font=FONTS["body_sm"],
            text_color=COLORS["warning"],
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
            height=130,
        )
        self.log_frame.grid(
            row=1, column=1, sticky="ew", padx=(0, 10), pady=(4, 10)
        )
        self.log_frame.grid_propagate(False)
        self.log_frame.grid_rowconfigure(1, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_columnconfigure(1, weight=0)

        self.log_title = ctk.CTkLabel(
            self.log_frame,
            text="\u64cd\u4f5c\u65e5\u5fd7",
            font=FONTS["label"],
            text_color=COLORS["text_muted"],
        )
        self.log_title.grid(row=0, column=0, padx=12, pady=(6, 2), sticky="w")

        self.btn_scroll_bottom_log = ctk.CTkButton(
            self.log_frame,
            text="\u5e95\u90e8",
            width=60,
            height=24,
            corner_radius=RADIUS_SM,
            font=("Segoe UI", 11),
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_muted"],
            hover_color=COLORS["bg_hover"],
            command=self.scroll_log_to_bottom,
        )
        self.btn_scroll_bottom_log.grid(row=0, column=1, padx=(0, 12), pady=(6, 2), sticky="e")

        self.log_text = ctk.CTkTextbox(
            self.log_frame,
            font=FONTS["mono"],
            fg_color=COLORS["bg_card"],
            border_width=0,
            text_color=COLORS["text_muted"],
        )
        self.log_text.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=(0, 6))
        self.log_text.configure(state="disabled")

        self._setup_log_tags()

    def _setup_log_tags(self):
        self.log_text.tag_config("INFO", foreground=_c("info"))
        self.log_text.tag_config("SUCCESS", foreground=_c("success"))
        self.log_text.tag_config("ERROR", foreground=_c("error"))
        self.log_text.tag_config("WARN", foreground=_c("warning"))
        self.log_text.tag_config("TIMESTAMP", foreground=_c("text_muted"))

    def add_log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
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
            self.log_text.insert("end", f"[{ts}] ", "TIMESTAMP")
            self.log_text.insert("end", f"[{lvl}] ", lvl)
            self.log_text.insert("end", f"{msg}\n", None)

        self.log_text.configure(state="disabled")
        self.log_text.see("end")

    def scroll_log_to_bottom(self):
        self.log_text.see("end")

    def _build_main_area(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.main_header = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.main_header.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 12))
        self.main_header.grid_columnconfigure(0, weight=1)
        self.main_header.grid_columnconfigure(1, weight=0)

        self.main_title = ctk.CTkLabel(
            self.main_header,
            text="\u6211\u7684\u96a7\u9053",
            font=FONTS["heading"],
            text_color=COLORS["text"],
            anchor="w",
        )
        self.main_title.grid(row=0, column=0, sticky="w")

        self.btn_add_quick = ctk.CTkButton(
            self.main_header,
            text="+ \u6dfb\u52a0",
            command=self.open_add_dialog,
            width=90,
            height=32,
            corner_radius=RADIUS_SM,
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="white",
        )
        self.btn_add_quick.grid(row=0, column=1, sticky="e")

        self.tunnel_count_label = ctk.CTkLabel(
            self.main_header,
            text="",
            font=FONTS["body_sm"],
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.tunnel_count_label.grid(
            row=1, column=0, columnspan=2, sticky="w", padx=(2, 0), pady=(4, 0)
        )

        self.main_frame = ctk.CTkScrollableFrame(
            self.main_container,
            corner_radius=RADIUS_MD,
            fg_color="transparent",
            border_width=0,
        )
        self.main_frame.grid(row=1, column=0, sticky="nsew", pady=0)
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.empty_state = ctk.CTkFrame(
            self.main_container,
            corner_radius=RADIUS_MD,
            fg_color=COLORS["bg_card"],
            border_width=1,
            border_color=COLORS["border_light"],
        )
        self.empty_state.grid(row=1, column=0, sticky="nsew")
        self.empty_state.grid_columnconfigure(0, weight=1)
        self.empty_state.grid_rowconfigure(0, weight=1)

        empty_inner = ctk.CTkFrame(self.empty_state, fg_color="transparent")
        empty_inner.grid(row=0, column=0)

        self.empty_icon = ctk.CTkLabel(
            empty_inner,
            text="\U0001f4e1",
            font=ctk.CTkFont(size=32),
            text_color=COLORS["text_muted"],
        )
        self.empty_icon.grid(row=0, column=0, pady=(0, 10))

        self.empty_title = ctk.CTkLabel(
            empty_inner,
            text="\u8fd8\u6ca1\u6709\u96a7\u9053",
            font=FONTS["heading_sm"],
            text_color=COLORS["text_secondary"],
        )
        self.empty_title.grid(row=1, column=0, pady=(0, 4))

        self.empty_desc = ctk.CTkLabel(
            empty_inner,
            text="\u70b9\u51fb\u300c\u6dfb\u52a0\u96a7\u9053\u300d\u6765\u521b\u5efa\u4f60\u7684\u7b2c\u4e00\u4e2a SSH \u96a7\u9053",
            font=FONTS["body_sm"],
            text_color=COLORS["text_muted"],
        )
        self.empty_desc.grid(row=2, column=0, pady=(0, 14))

        self.empty_btn = ctk.CTkButton(
            empty_inner,
            text="+ \u6dfb\u52a0\u96a7\u9053",
            command=self.open_add_dialog,
            width=130,
            height=34,
            corner_radius=RADIUS_SM,
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="white",
        )
        self.empty_btn.grid(row=3, column=0)

        self.empty_state.grid(row=1, column=0, sticky="nsew")
        self.main_frame.grid_remove()

    def start_daemon(self):
        self.add_log("\u6b63\u5728\u542f\u52a8\u5b88\u62a4\u8fdb\u7a0b...", "INFO")
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
        self.add_log("\u5b88\u62a4\u8fdb\u7a0b\u542f\u52a8\u547d\u4ee4\u5df2\u53d1\u9001", "INFO")
        messagebox.showinfo(
            "\u5b88\u62a4\u8fdb\u7a0b", "\u5b88\u62a4\u8fdb\u7a0b\u5df2\u5728\u540e\u53f0\u542f\u52a8\u3002"
        )

    def stop_daemon(self):
        try:
            requests.post(f"{DAEMON_URL}/shutdown", timeout=3)
            self.add_log("\u5173\u95ed\u5b88\u62a4\u8fdb\u7a0b\u8bf7\u6c42\u5df2\u53d1\u9001", "INFO")
            error_color = COLORS["error"][0] if isinstance(COLORS["error"], tuple) else COLORS["error"]
            self.update_status_indicator("\u5b88\u62a4\u8fdb\u7a0b: \u79bb\u7ebf", error_color)
            messagebox.showinfo(
                "\u5b88\u62a4\u8fdb\u7a0b", "\u5b88\u62a4\u8fdb\u7a0b\u5173\u95ed\u8bf7\u6c42\u5df2\u53d1\u9001\u3002"
            )
        except requests.exceptions.ConnectionError:
            self.add_log("\u5b88\u62a4\u8fdb\u7a0b\u672a\u8fd0\u884c", "WARN")
            messagebox.showinfo("\u5b88\u62a4\u8fdb\u7a0b", "\u5b88\u62a4\u8fdb\u7a0b\u672a\u8fd0\u884c\u3002")
        except Exception as e:
            self.add_log(f"\u5173\u95ed\u5b88\u62a4\u8fdb\u7a0b\u5931\u8d25: {e}", "ERROR")
            messagebox.showerror("\u9519\u8bef", f"\u5173\u95ed\u5b88\u62a4\u8fdb\u7a0b\u5931\u8d25: {e}")

    def import_config(self):
        path = filedialog.askopenfilename(
            filetypes=[("YAML \u6587\u4ef6", "*.yaml"), ("\u6240\u6709\u6587\u4ef6", "*.*")]
        )
        if path:
            try:
                config_manager.import_config(path)
                self.notify_daemon()
                self.add_log(f"\u914d\u7f6e\u5df2\u4ece {path} \u5bfc\u5165", "SUCCESS")
                messagebox.showinfo("\u6210\u529f", "\u914d\u7f6e\u5bfc\u5165\u6210\u529f\u3002")
            except Exception as e:
                self.add_log(f"\u914d\u7f6e\u5bfc\u5165\u5931\u8d25: {e}", "ERROR")
                messagebox.showerror("\u9519\u8bef", f"\u5bfc\u5165\u5931\u8d25: {e}")

    def export_config(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".yaml", filetypes=[("YAML \u6587\u4ef6", "*.yaml")]
        )
        if path:
            try:
                config_manager.export_config(path)
                self.add_log(f"\u914d\u7f6e\u5df2\u5bfc\u51fa\u5230 {path}", "SUCCESS")
                messagebox.showinfo("\u6210\u529f", "\u914d\u7f6e\u5bfc\u51fa\u6210\u529f\u3002")
            except Exception as e:
                self.add_log(f"\u914d\u7f6e\u5bfc\u51fa\u5931\u8d25: {e}", "ERROR")
                messagebox.showerror("\u9519\u8bef", f"\u5bfc\u51fa\u5931\u8d25: {e}")

    def notify_daemon(self):
        try:
            requests.post(f"{DAEMON_URL}/config/reload", timeout=2)
        except Exception:
            pass

    def open_add_dialog(self, edit_name=None):
        dialog = ctk.CTkToplevel(self)
        is_edit = edit_name is not None
        dialog.title("\u7f16\u8f91\u96a7\u9053" if is_edit else "\u6dfb\u52a0\u96a7\u9053")
        dialog.configure(fg_color=COLORS["bg_card"])
        dialog.resizable(False, False)

        dialog.grid_columnconfigure(0, weight=0)
        dialog.grid_columnconfigure(1, weight=1)

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (720 // 2)
        dialog.geometry(f"400x720+{x}+{y}")

        dialog.transient(self)
        dialog.grab_set()
        dialog.lift()

        FIELD_DEFS = [
            {
                "section": "\u57fa\u7840\u4fe1\u606f",
                "fields": [
                    {"key": "name", "label": "\u540d\u79f0", "placeholder": "\u96a7\u9053\u7684\u552f\u4e00\u6807\u8bc6"},
                ],
            },
            {
                "section": "SSH \u8fde\u63a5",
                "fields": [
                    {
                        "key": "tunnel_type",
                        "label": "\u96a7\u9053\u7c7b\u578b",
                        "type": "option",
                        "values": ["local", "remote"],
                    },
                    {
                        "key": "ssh_host",
                        "label": "SSH \u4e3b\u673a",
                        "placeholder": "SSH\u670d\u52a1\u5668\u5730\u5740",
                    },
                    {"key": "ssh_port", "label": "SSH \u7aef\u53e3", "placeholder": "22"},
                    {"key": "ssh_user", "label": "SSH \u7528\u6237", "placeholder": "\u7528\u6237\u540d"},
                    {
                        "key": "ssh_password",
                        "label": "SSH \u5bc6\u7801",
                        "placeholder": "\u7559\u7a7a\u4f7f\u7528\u79c1\u94a5",
                    },
                    {
                        "key": "ssh_pkey",
                        "label": "\u79c1\u94a5\u8def\u5f84",
                        "placeholder": "~/.ssh/id_rsa",
                    },
                ],
            },
            {
                "section": "\u96a7\u9053\u8bbe\u7f6e",
                "fields": [
                    {
                        "key": "local_bind_port",
                        "label": "\u672c\u5730\u7aef\u53e3",
                        "placeholder": "\u672c\u673a\u76d1\u542c\u7aef\u53e3",
                    },
                    {
                        "key": "remote_bind_host",
                        "label": "\u8fdc\u7aef\u4e3b\u673a",
                        "placeholder": "127.0.0.1",
                    },
                    {
                        "key": "remote_bind_port",
                        "label": "\u8fdc\u7aef\u7aef\u53e3",
                        "placeholder": "\u76ee\u6807\u7aef\u53e3",
                    },
                ],
            },
        ]

        DEFAULTS = {
            "ssh_port": "22",
            "tunnel_type": "local",
            "remote_bind_host": "127.0.0.1",
        }

        FIELD_HINTS = {}

        HELP_TEXTS = {
            "local": "\u3010\u6b63\u5411\u96a7\u9053\u3011\u8bbf\u95ee\u8fdc\u7a0b\u670d\u52a1\u5668\u4e0a\u7684\u670d\u52a1\n\u6d41\u5411: \u672c\u673a\u7aef\u53e3 -> SSH\u670d\u52a1\u5668 -> \u8fdc\u7aef\u76ee\u6807\u7aef\u53e3\n\u793a\u4f8b: \u672c\u673a13306 -> SSH\u670d\u52a1\u5668 -> \u8fdc\u7aefMySQL 3306",
            "remote": "\u3010\u53cd\u5411\u96a7\u9053\u3011\u8ba9\u5916\u7f51\u8bbf\u95ee\u672c\u673a\u670d\u52a1\n\u6d41\u5411: SSH\u670d\u52a1\u5668\u76d1\u542c\u7aef\u53e3 -> \u672c\u673a\u670d\u52a1\u7aef\u53e3\n\u793a\u4f8b: SSH\u670d\u52a1\u56688080 -> \u672c\u673aWeb\u5e94\u75288080\n\u524d\u63d0: SSH\u670d\u52a1\u5668\u9700\u5f00\u542f GatewayPorts",
        }

        entries = {}

        title_label = ctk.CTkLabel(
            dialog,
            text="\u7f16\u8f91\u96a7\u9053" if is_edit else "\u6dfb\u52a0\u96a7\u9053",
            font=FONTS["heading_sm"],
            text_color=COLORS["text"],
        )
        title_label.grid(
            row=0, column=0, columnspan=2, padx=20, pady=(16, 4), sticky="w"
        )

        help_frame = ctk.CTkFrame(
            dialog,
            fg_color=COLORS["bg_input"],
            corner_radius=RADIUS_SM,
            border_width=1,
            border_color=COLORS["border_light"],
        )
        help_frame.grid(
            row=1, column=0, columnspan=2, padx=20, pady=(0, 8), sticky="ew"
        )
        help_frame.grid_columnconfigure(0, weight=1)

        help_label = ctk.CTkLabel(
            help_frame,
            text=HELP_TEXTS["local"],
            font=FONTS["body_sm"],
            justify="left",
            text_color=COLORS["text_secondary"],
        )
        help_label.grid(row=0, column=0, padx=10, pady=8, sticky="w")

        def update_help_text(choice):
            help_label.configure(text=HELP_TEXTS.get(choice, HELP_TEXTS["local"]))

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

        current_row = 2
        LABEL_WIDTH = 80

        for group in FIELD_DEFS:
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
                pady=(8, 2),
                sticky="w",
            )
            current_row += 1

            for field_def in group["fields"]:
                field_key = field_def["key"]
                field_label = field_def["label"]

                lbl = ctk.CTkLabel(
                    dialog,
                    text=field_label,
                    font=FONTS["label"],
                    text_color=COLORS["text_secondary"],
                    width=LABEL_WIDTH,
                    anchor="e",
                )
                lbl.grid(row=current_row, column=0, padx=(20, 8), pady=3, sticky="e")

                input_frame = ctk.CTkFrame(dialog, fg_color="transparent")
                input_frame.grid(row=current_row, column=1, padx=(0, 20), pady=3, sticky="ew")
                input_frame.grid_columnconfigure(0, weight=1)
                input_frame.grid_columnconfigure(1, weight=0)

                if field_def.get("type") == "option":
                    seg = ctk.CTkSegmentedButton(
                        input_frame,
                        values=field_def["values"],
                        height=30,
                        corner_radius=RADIUS_SM,
                        font=FONTS["body"],
                        fg_color=COLORS["bg_input"],
                        selected_color=COLORS["primary"],
                        selected_hover_color=COLORS["primary_hover"],
                        unselected_color=COLORS["bg_input"],
                        unselected_hover_color=COLORS["bg_hover"],
                        text_color=COLORS["text"],
                        command=update_help_text,
                    )
                    if is_edit and "tunnel_type" in initial_values:
                        seg.set(initial_values["tunnel_type"])
                    else:
                        seg.set(DEFAULTS.get("tunnel_type", "local"))
                    seg.grid(row=0, column=0, sticky="ew")
                    entries[field_key] = seg
                else:
                    ent = ctk.CTkEntry(
                        input_frame,
                        height=30,
                        corner_radius=RADIUS_SM,
                        border_width=1,
                        fg_color=COLORS["bg_input"],
                        border_color=COLORS["border_light"],
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
                    ent.grid(row=0, column=0, sticky="ew")
                    entries[field_key] = ent

                current_row += 1

            if group != FIELD_DEFS[-1]:
                sep = ctk.CTkFrame(
                    dialog, height=1, fg_color=COLORS["border_light"]
                )
                sep.grid(
                    row=current_row, column=0, columnspan=2, padx=20, pady=(6, 0), sticky="ew"
                )
                current_row += 1

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.grid(row=current_row, column=0, columnspan=2, pady=(16, 16))

        def _save_tunnel_from_dialog():
            name = entries["name"].get()
            if not name:
                messagebox.showerror("\u9519\u8bef", "\u8bf7\u8f93\u5165\u96a7\u9053\u540d\u79f0")
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
                    if edit_name in config_manager.config.tunnels:
                        config_manager.remove_tunnel(edit_name)
                config_manager.add_tunnel(name, conf)
                self.notify_daemon()
                self.add_log(
                    f"\u96a7\u9053 '{name}' {'\u66f4\u65b0' if is_edit else '\u6dfb\u52a0'}\u6210\u529f",
                    "SUCCESS",
                )
                dialog.destroy()
            except Exception as e:
                self.add_log(f"\u4fdd\u5b58\u96a7\u9053\u5931\u8d25: {e}", "ERROR")
                messagebox.showerror("\u9519\u8bef", str(e))

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="\u53d6\u6d88",
            width=100,
            height=34,
            corner_radius=RADIUS_SM,
            font=FONTS["button"],
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["bg_hover"],
            command=dialog.destroy,
        )
        btn_cancel.grid(row=0, column=0, padx=(0, 10))

        btn_save = ctk.CTkButton(
            btn_frame,
            text="\u4fdd\u5b58",
            width=100,
            height=34,
            corner_radius=RADIUS_SM,
            font=FONTS["button"],
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="white",
            command=_save_tunnel_from_dialog,
        )
        btn_save.grid(row=0, column=1)

        dialog.bind("<Return>", lambda e: _save_tunnel_from_dialog())

    def update_status_indicator(self, text, color_hex):
        self.status_label.configure(text=text, text_color=color_hex)
        self.status_dot.configure(fg_color=color_hex)

    def poll_daemon(self):
        was_offline = False
        while self.running:
            try:
                r = requests.get(f"{DAEMON_URL}/tunnels", timeout=2)
                data = r.json()
                if was_offline:
                    self.add_log("\u5b88\u62a4\u8fdb\u7a0b\u5df2\u8fde\u63a5", "SUCCESS")
                    was_offline = False
                success_color = COLORS["success"][0] if isinstance(COLORS["success"], tuple) else COLORS["success"]
                self.after(
                    0, self.update_status_indicator, "\u5b88\u62a4\u8fdb\u7a0b: \u5728\u7ebf", success_color
                )
                self.after(0, self.update_tunnels_ui, data)
            except requests.exceptions.ConnectionError:
                if not was_offline:
                    self.add_log("\u5b88\u62a4\u8fdb\u7a0b\u8fde\u63a5\u65ad\u5f00", "WARN")
                    was_offline = True
                error_color = COLORS["error"][0] if isinstance(COLORS["error"], tuple) else COLORS["error"]
                self.after(
                    0, self.update_status_indicator, "\u5b88\u62a4\u8fdb\u7a0b: \u79bb\u7ebf", error_color
                )
                local_data = {
                    name: {"config": conf.model_dump(), "status": "offline"}
                    for name, conf in config_manager.config.tunnels.items()
                }
                self.after(0, self.update_tunnels_ui, local_data)
            except Exception:
                pass
            time.sleep(2)

    def update_tunnels_ui(self, data):
        current_names = set(data.keys())
        displayed_names = set(self.frames.keys())

        if len(current_names) == 0:
            self.empty_state.grid(row=1, column=0, sticky="nsew")
            self.empty_state.lift()
            self.main_frame.grid_remove()
            self.tunnel_count_label.configure(text="")
        else:
            self.main_frame.grid(row=1, column=0, sticky="nsew")
            self.main_frame.lift()
            self.empty_state.grid_remove()

            active_count = sum(
                1 for info in data.values() if info.get("status") == "active"
            )
            total_count = len(current_names)
            if active_count > 0:
                self.tunnel_count_label.configure(
                    text=f"\u5171 {total_count} \u4e2a\u96a7\u9053\uff0c{active_count} \u4e2a\u6d3b\u8dc3"
                )
            else:
                self.tunnel_count_label.configure(text=f"\u5171 {total_count} \u4e2a\u96a7\u9053")

        for name in displayed_names - current_names:
            self.frames[name].destroy()
            del self.frames[name]

        for i, name in enumerate(sorted(current_names)):
            info = data[name]
            config = info.get("config", {})
            status = info.get("status", "offline")

            if name not in self.frames:
                card = TunnelCard(
                    self.main_frame,
                    name=name,
                    config=config,
                    status=status,
                    on_toggle_callback=self.toggle_tunnel,
                    on_edit_callback=self.open_add_dialog,
                    on_delete_callback=self.delete_tunnel,
                )
                card.grid(row=i, column=0, sticky="ew", pady=(0, 8), padx=0)
                self.frames[name] = card
            else:
                card = self.frames[name]
                card.grid(row=i)
                card.configure_tunnel(name, config, status)

    def toggle_tunnel(self, name, action):
        try:
            r = requests.post(f"{DAEMON_URL}/tunnels/{name}/{action}", timeout=2)
            self.add_log(
                f"\u96a7\u9053 '{name}' {action}\u64cd\u4f5c\u5df2\u6267\u884c",
                "SUCCESS" if r.status_code == 200 else "ERROR",
            )
        except requests.exceptions.ConnectionError:
            self.add_log(
                f"\u65e0\u6cd5\u8fde\u63a5\u5b88\u62a4\u8fdb\u7a0b\uff0c\u96a7\u9053 '{name}' {action}\u5931\u8d25",
                "ERROR",
            )
            messagebox.showerror(
                "\u9519\u8bef", f"\u65e0\u6cd5{action}\u96a7\u9053\uff1a\u5b88\u62a4\u8fdb\u7a0b\u672a\u8fd0\u884c"
            )
        except Exception as e:
            self.add_log(f"\u96a7\u9053 '{name}' {action}\u5931\u8d25: {e}", "ERROR")
            messagebox.showerror("\u9519\u8bef", f"\u65e0\u6cd5{action}\u96a7\u9053: {e}")

    def delete_tunnel(self, name):
        if messagebox.askyesno("\u786e\u8ba4", f"\u786e\u5b9a\u8981\u5220\u9664\u96a7\u9053 {name} \u5417\uff1f"):
            config_manager.remove_tunnel(name)
            self.notify_daemon()
            self.add_log(f"\u96a7\u9053 '{name}' \u5df2\u5220\u9664", "INFO")

    def destroy(self):
        self.running = False
        super().destroy()


if __name__ == "__main__":
    app = TunnelApp()
    app.mainloop()
