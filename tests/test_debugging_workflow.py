"""
Automated Tests for NOVA Autonomous Debugging Loop
"""
import unittest
import tempfile
import shutil
from pathlib import Path

from nova.agent.coding_agent import CodingAgent
from nova.permissions.permission_manager import PermissionManager


class TestDebuggingWorkflow(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_root = Path(self.temp_dir) / "workspace"
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        self.permission_manager = PermissionManager(workspace_root=self.workspace_root)
        self.agent = CodingAgent(
            workspace_root=self.workspace_root,
            permission_manager=self.permission_manager,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_workflow_successful_execution(self):
        main_file = self.workspace_root / "main.py"
        main_file.write_text("print('Hello Coding Agent')\n", encoding="utf-8")

        res = self.agent.execute_workflow(
            task_description="Run hello world app",
            user_approved_venv=True,
            user_approved_install=True,
            user_approved_run=True,
            user_approved_fix=True,
        )

        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "COMPLETED_SUCCESS")
        self.assertIn("Hello Coding Agent", res["execution_result"]["stdout"])

    def test_workflow_permission_guard(self):
        main_file = self.workspace_root / "main.py"
        main_file.write_text("print('Need permission')\n", encoding="utf-8")

        res = self.agent.execute_workflow(
            task_description="Run app without permission",
            user_approved_venv=True,
            user_approved_install=True,
            user_approved_run=False,  # Denied execution permission
        )

        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "WAITING_FOR_PERMISSION")
        self.assertTrue(len(res["action_proposals"]) > 0)

    def test_workflow_max_debug_attempts_cap(self):
        # Write a file with unfixable runtime error
        main_file = self.workspace_root / "main.py"
        main_file.write_text("raise RuntimeError('Unrecoverable test crash')\n", encoding="utf-8")

        res = self.agent.execute_workflow(
            task_description="Debug failing app",
            user_approved_venv=True,
            user_approved_install=True,
            user_approved_run=True,
            user_approved_fix=True,
        )

        self.assertFalse(res["success"])
        self.assertLessEqual(res["debug_attempts"], CodingAgent.MAX_DEBUG_ATTEMPTS)


if __name__ == "__main__":
    unittest.main()
