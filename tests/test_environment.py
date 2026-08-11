"""
Automated Tests for NOVA Environment Manager Subsystem
"""
import sys
import unittest
import tempfile
import shutil
from pathlib import Path

from nova.environment.environment_manager import EnvironmentManager, EnvironmentError
from nova.permissions.permission_manager import PermissionManager


class TestEnvironmentManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_root = Path(self.temp_dir) / "workspace"
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        self.permission_manager = PermissionManager(workspace_root=self.workspace_root)
        self.env_manager = EnvironmentManager(
            workspace_root=self.workspace_root,
            permission_manager=self.permission_manager,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_language_detection(self):
        (self.workspace_root / "main.py").touch()
        (self.workspace_root / "requirements.txt").touch()

        lang = self.env_manager.detect_language()
        self.assertEqual(lang["primary"], "Python")
        self.assertIn("Python", lang["detected"])

    def test_python_environment_detection(self):
        info = self.env_manager.detect_python_environment()
        self.assertIn("python_executable", info)
        self.assertIn("python_version", info)
        self.assertFalse(info["venv_found"])

    def test_virtual_environment_creation_requires_permission(self):
        res = self.env_manager.create_virtual_environment(venv_name=".venv", user_approved=False)
        self.assertFalse(res["success"])
        self.assertTrue(res.get("permission_required"))
        self.assertIn("proposed_action", res)

    def test_virtual_environment_creation_approved(self):
        res = self.env_manager.create_virtual_environment(venv_name=".venv", user_approved=True)
        self.assertTrue(res["success"])
        self.assertTrue(res["created"])
        self.assertTrue((self.workspace_root / ".venv").is_dir())

    def test_virtual_environment_creation_security_boundary(self):
        with self.assertRaises(EnvironmentError):
            self.env_manager.create_virtual_environment(venv_name="../escaping_venv", user_approved=True)

    def test_health_check(self):
        health = self.env_manager.health_check()
        self.assertIn("status", health)
        self.assertIn("python_executable", health)
        self.assertIn("pip_available", health)


if __name__ == "__main__":
    unittest.main()
