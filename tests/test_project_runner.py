"""
Automated Tests for NOVA Project Runner Subsystem
"""
import unittest
import tempfile
import shutil
from pathlib import Path

from nova.environment.environment_manager import EnvironmentManager
from nova.project.project_runner import ProjectRunner
from nova.permissions.permission_manager import PermissionManager


class TestProjectRunner(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_root = Path(self.temp_dir) / "workspace"
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        self.permission_manager = PermissionManager(workspace_root=self.workspace_root)
        self.env_manager = EnvironmentManager(
            workspace_root=self.workspace_root,
            permission_manager=self.permission_manager,
        )
        self.runner = ProjectRunner(
            workspace_root=self.workspace_root,
            environment_manager=self.env_manager,
            permission_manager=self.permission_manager,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_find_entry_point_discovery(self):
        main_file = self.workspace_root / "main.py"
        main_file.write_text("print('Hello Test')\n", encoding="utf-8")

        ep = self.runner.find_entry_point()
        self.assertIsNotNone(ep)
        self.assertEqual(ep.name, "main.py")

    def test_run_project_requires_permission(self):
        main_file = self.workspace_root / "main.py"
        main_file.write_text("print('Hello Permission')\n", encoding="utf-8")

        res = self.runner.run_project(user_approved=False)
        self.assertFalse(res["success"])
        self.assertTrue(res.get("permission_required"))
        self.assertIn("proposed_action", res)

    def test_run_project_approved_execution(self):
        main_file = self.workspace_root / "main.py"
        main_file.write_text("print('SUCCESS_MARKER')\n", encoding="utf-8")

        res = self.runner.run_project(user_approved=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("SUCCESS_MARKER", res["stdout"])

    def test_run_project_captures_stderr_and_exit_code(self):
        app_file = self.workspace_root / "app.py"
        app_file.write_text("import sys\nsys.stderr.write('ERROR_MARKER\\n')\nsys.exit(42)\n", encoding="utf-8")

        res = self.runner.run_project(entry_point="app.py", user_approved=True)
        self.assertFalse(res["success"])
        self.assertEqual(res["exit_code"], 42)
        self.assertIn("ERROR_MARKER", res["stderr"])


if __name__ == "__main__":
    unittest.main()
