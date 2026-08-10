"""
Automated Security & Path Traversal Protection Tests
"""
import unittest
import tempfile
import shutil
from pathlib import Path

from nova.core.config import ConfigManager
from nova.permissions.permission_manager import PermissionManager
from nova.services.filesystem_service import FileSystemService


class TestSecurityAndPathProtection(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_root = Path(self.temp_dir) / "workspace"
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        self.permission_manager = PermissionManager(workspace_root=self.workspace_root)

        config_path = Path(self.temp_dir) / "settings.json"
        self.config_manager = ConfigManager(config_path)
        self.config_manager.load()
        self.fs_service = FileSystemService(self.config_manager)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_normal_allowed_paths_work(self):
        allowed_paths = [
            "main.py",
            "src/utils.py",
            "data/logs/app.log",
            "nested/deep/file.txt",
        ]
        for path_str in allowed_paths:
            is_safe = self.permission_manager.is_safe_path(path_str)
            self.assertTrue(is_safe, f"Path '{path_str}' should be allowed inside workspace")

            fs_safe = self.fs_service.is_safe_path(path_str, root_dir=self.workspace_root)
            self.assertTrue(fs_safe, f"FileSystemService should allow '{path_str}'")

    def test_path_traversal_rejected(self):
        traversal_paths = [
            "../secret.txt",
            "../../etc/passwd",
            "src/../../outside.txt",
            "..\\windows\\system32",
        ]
        for path_str in traversal_paths:
            is_safe = self.permission_manager.is_safe_path(path_str)
            self.assertFalse(is_safe, f"Path traversal '{path_str}' must be rejected")

            fs_safe = self.fs_service.is_safe_path(path_str, root_dir=self.workspace_root)
            self.assertFalse(fs_safe, f"FileSystemService must reject '{path_str}'")

    def test_unauthorized_absolute_paths_rejected(self):
        # Create an outside directory
        outside_dir = Path(self.temp_dir) / "outside"
        outside_dir.mkdir(parents=True, exist_ok=True)
        forbidden_file = outside_dir / "forbidden.txt"

        is_safe = self.permission_manager.is_safe_path(forbidden_file)
        self.assertFalse(is_safe, f"Absolute path '{forbidden_file}' outside workspace must be rejected")

        fs_safe = self.fs_service.is_safe_path(forbidden_file, root_dir=self.workspace_root)
        self.assertFalse(fs_safe, f"FileSystemService must reject absolute path '{forbidden_file}'")


if __name__ == "__main__":
    unittest.main()
