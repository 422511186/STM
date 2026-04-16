import socket
import threading
import time
import unittest

import paramiko

from core.config import TunnelConfig
from core.tunnel import TunnelController, TunnelState


def get_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class EchoServer(threading.Thread):
    def __init__(self, host: str = "127.0.0.1", port: int | None = None):
        super().__init__(daemon=True)
        self.host = host
        self.port = port or get_free_port()
        self._stop = threading.Event()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(5)

    def run(self):
        while not self._stop.is_set():
            try:
                self._sock.settimeout(0.2)
                conn, _ = self._sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket):
        with conn:
            conn.settimeout(1)
            while not self._stop.is_set():
                try:
                    data = conn.recv(4096)
                except TimeoutError:
                    continue
                except OSError:
                    break
                if not data:
                    break
                conn.sendall(data)

    def stop(self):
        self._stop.set()
        try:
            self._sock.close()
        except OSError:
            pass


class _SSHServer(paramiko.ServerInterface):
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self._direct = {}

    def check_auth_password(self, username, password):
        if username == self.username and password == self.password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_request(self, kind, chanid):
        if kind in ("session", "direct-tcpip"):
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_direct_tcpip_request(self, chanid, origin, destination):
        self._direct[chanid] = destination
        return paramiko.OPEN_SUCCEEDED


class SSHTestServer:
    def __init__(self, host: str = "127.0.0.1", port: int | None = None, username: str = "u", password: str = "p"):
        self.host = host
        self.port = port or get_free_port()
        self.username = username
        self.password = password
        self._stop = threading.Event()
        self._host_key = paramiko.RSAKey.generate(1024)
        self._listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listen_sock.bind((self.host, self.port))
        self._listen_sock.listen(100)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._transports: list[paramiko.Transport] = []

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        try:
            self._listen_sock.close()
        except OSError:
            pass
        for t in list(self._transports):
            try:
                t.close()
            except Exception:
                pass

    def _serve(self):
        while not self._stop.is_set():
            try:
                self._listen_sock.settimeout(0.2)
                client, _ = self._listen_sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()

    def _handle_client(self, client: socket.socket):
        t = paramiko.Transport(client)
        self._transports.append(t)
        server = _SSHServer(self.username, self.password)
        try:
            t.add_server_key(self._host_key)
            t.start_server(server=server)
            while not self._stop.is_set() and t.is_active():
                chan = t.accept(timeout=0.2)
                if chan is None:
                    continue
                dest = server._direct.get(chan.chanid)
                if not dest:
                    chan.close()
                    continue
                threading.Thread(target=self._bridge, args=(chan, dest), daemon=True).start()
        except Exception:
            pass
        finally:
            try:
                t.close()
            except Exception:
                pass

    def _bridge(self, chan: paramiko.Channel, dest: tuple[str, int]):
        try:
            sock = socket.create_connection(dest, timeout=3)
        except Exception:
            try:
                chan.close()
            except Exception:
                pass
            return

        def c2s():
            try:
                while True:
                    data = chan.recv(4096)
                    if not data:
                        break
                    sock.sendall(data)
            except Exception:
                pass
            finally:
                try:
                    sock.shutdown(socket.SHUT_WR)
                except Exception:
                    pass

        def s2c():
            try:
                while True:
                    data = sock.recv(4096)
                    if not data:
                        break
                    chan.sendall(data)
            except Exception:
                pass
            finally:
                try:
                    chan.shutdown_write()
                except Exception:
                    pass

        t1 = threading.Thread(target=c2s, daemon=True)
        t2 = threading.Thread(target=s2c, daemon=True)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)
        try:
            sock.close()
        except Exception:
            pass
        try:
            chan.close()
        except Exception:
            pass


class TestTunnelE2E(unittest.TestCase):
    def test_real_port_forwarding(self):
        echo = EchoServer()
        echo.start()

        ssh = SSHTestServer(username="test", password="pass")
        ssh.start()

        local_port = get_free_port()
        cfg = TunnelConfig(
            ssh_host="127.0.0.1",
            ssh_port=ssh.port,
            ssh_user="test",
            ssh_password="pass",
            local_bind_port=local_port,
            remote_bind_host="127.0.0.1",
            remote_bind_port=echo.port,
        )
        ctrl = TunnelController("e2e", cfg)
        try:
            ctrl.start()
            deadline = time.time() + 10
            while time.time() < deadline and ctrl.state not in (TunnelState.ACTIVE, TunnelState.ERROR):
                time.sleep(0.1)
            self.assertEqual(ctrl.state, TunnelState.ACTIVE, ctrl.error_message)

            with socket.create_connection(("127.0.0.1", local_port), timeout=3) as s:
                payload = b"hello-e2e"
                s.sendall(payload)
                got = s.recv(1024)
                self.assertEqual(got, payload)
        finally:
            ctrl.stop()
            ssh.stop()
            echo.stop()


if __name__ == "__main__":
    unittest.main()

