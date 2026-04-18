import sys
import os

def print_help():
    print("SSH 隧道管理器")
    print("用法：")
    print("  python main.py           - 启动 GUI")
    print("  python main.py tui       - 启动 TUI (终端界面)")
    print("  python main.py cli ...   - 使用 CLI")
    print("  python main.py daemon    - 前台运行守护进程")

if __name__ == "__main__":
    # Ensure current directory is in PYTHONPATH
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "cli":
            from cli.main import app
            sys.argv.pop(1)
            app()
        elif cmd == "tui":
            from tui.main import run_app
            run_app()
        elif cmd == "daemon":
            from daemon.server import run_server
            run_server()
        elif cmd in ("-h", "--help", "help"):
            print_help()
        else:
            print(f"未知命令：{cmd}")
            print_help()
    else:
        # Default to GUI
        try:
            from gui.main import TunnelApp
            app = TunnelApp()
            app.mainloop()
        except ImportError as e:
            print(f"启动 GUI 失败：{e}")
            print("您可能需要桌面环境或使用 CLI。")
