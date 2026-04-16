import os
import subprocess
import sys
import socket
import tempfile
import time
import unittest

import requests


def wait_for_port(url: str, timeout_s: float = 10.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            requests.get(url, timeout=0.5)
            return True
        except Exception:
            time.sleep(0.2)
    return False


def get_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class TestDaemonCliSmoke(unittest.TestCase):
    def test_daemon_and_cli_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            config_path = os.path.join(tmp, "config.yaml")
            port = get_free_port()
            env = os.environ.copy()
            env["PYTHONPATH"] = repo_root
            env["SSH_TUNNEL_MANAGER_CONFIG"] = config_path
            env["SSH_TUNNEL_MANAGER_PORT"] = str(port)

            daemon = subprocess.Popen(
                [sys.executable, "-m", "daemon.server"],
                cwd=repo_root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                base_url = f"http://127.0.0.1:{port}"
                self.assertTrue(wait_for_port(f"{base_url}/tunnels", timeout_s=10.0))

                r = subprocess.run(
                    [sys.executable, "main.py", "cli", "add", "t1", "127.0.0.1", "test", "10081", "1"],
                    cwd=repo_root,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.assertIn("added successfully", r.stdout.lower())

                r = subprocess.run(
                    [sys.executable, "main.py", "cli", "status"],
                    cwd=repo_root,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                self.assertIn("t1", r.stdout)

                subprocess.run(
                    [sys.executable, "main.py", "cli", "start", "t1"],
                    cwd=repo_root,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=True,
                )

                time.sleep(1.5)
                tunnels = requests.get(f"{base_url}/tunnels", timeout=2).json()
                self.assertIn("t1", tunnels)
                self.assertIn(tunnels["t1"]["status"], ["connecting", "error", "active"])
            finally:
                try:
                    requests.post(f"{base_url}/shutdown", timeout=1)
                except Exception:
                    pass
                daemon.terminate()
                try:
                    daemon.wait(timeout=5)
                except Exception:
                    daemon.kill()


if __name__ == "__main__":
    unittest.main()
