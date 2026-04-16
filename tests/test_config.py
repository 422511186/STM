import os
import tempfile
import unittest
import importlib


class TestConfigManager(unittest.TestCase):
    def test_roundtrip_export_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = os.path.join(tmp, "config.yaml")
            export_path = os.path.join(tmp, "export.yaml")
            os.environ["SSH_TUNNEL_MANAGER_CONFIG"] = config_path

            import core.config as config_module
            importlib.reload(config_module)

            cm = config_module.ConfigManager()
            tc = config_module.TunnelConfig(
                ssh_host="127.0.0.1",
                ssh_user="test",
                local_bind_port=10080,
                remote_bind_port=80,
            )
            cm.add_tunnel("t1", tc)

            self.assertTrue(os.path.exists(config_path))

            cm.export_config(export_path)
            self.assertTrue(os.path.exists(export_path))

            os.remove(config_path)
            self.assertFalse(os.path.exists(config_path))

            cm.import_config(export_path)
            self.assertTrue(os.path.exists(config_path))
            self.assertIn("t1", cm.config.tunnels)


if __name__ == "__main__":
    unittest.main()

