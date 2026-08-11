"""
Automated Tests for NOVA Dependency Manager Subsystem
"""
import unittest
import tempfile
import shutil
from pathlib import Path

from nova.environment.environment_manager import EnvironmentManager
from nova.environment.dependency_manager import DependencyManager
from nova.permissions.permission_manager import PermissionManager


class TestDependencyManager(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_root = Path(self.temp_dir) / "workspace"
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        self.permission_manager = PermissionManager(workspace_root=self.workspace_root)
        self.env_manager = EnvironmentManager(
            workspace_root=self.workspace_root,
            permission_manager=self.permission_manager,
        )
        self.dep_manager = DependencyManager(
            workspace_root=self.workspace_root,
            environment_manager=self.env_manager,
            permission_manager=self.permission_manager,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_dependency_files(self):
        (self.workspace_root / "requirements.txt").write_text("requests>=2.25.0\nflask\n", encoding="utf-8")

        detected = self.dep_manager.detect_dependency_files()
        self.assertIn("requirements.txt", detected["files_found"])
        self.assertTrue(detected["has_python_deps"])

    def test_parse_requirements_txt(self):
        req_file = self.workspace_root / "requirements.txt"
        req_file.write_text("# Comment\nrequests>=2.28.0\nflask==2.2.2\n-e .\nnumpy\n", encoding="utf-8")

        parsed = self.dep_manager.parse_python_requirements("requirements.txt")
        self.assertIn("requests", parsed)
        self.assertIn("flask", parsed)
        self.assertIn("numpy", parsed)
        self.assertNotIn("# Comment", parsed)

    def test_parse_pyproject_toml(self):
        pyproject = self.workspace_root / "pyproject.toml"
        pyproject.write_text('[project]\ndependencies = [\n    "requests>=2.0.0",\n    "urllib3"\n]\n', encoding="utf-8")

        parsed = self.dep_manager.parse_pyproject_toml("pyproject.toml")
        self.assertIn("requests", parsed)
        self.assertIn("urllib3", parsed)

    def test_check_missing_dependencies(self):
        (self.workspace_root / "requirements.txt").write_text("non_existent_fake_package_999\n", encoding="utf-8")

        check = self.dep_manager.check_missing_dependencies()
        self.assertIn("non_existent_fake_package_999", check["missing"])

    def test_install_dependency_requires_permission(self):
        res = self.dep_manager.install_dependency("requests", user_approved=False)
        self.assertFalse(res["success"])
        self.assertTrue(res.get("permission_required"))
        self.assertIn("proposed_action", res)

    def test_install_dependency_empty_name(self):
        res = self.dep_manager.install_dependency("", user_approved=True)
        self.assertFalse(res["success"])


if __name__ == "__main__":
    unittest.main()
