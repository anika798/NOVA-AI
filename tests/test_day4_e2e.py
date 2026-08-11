"""
Day 4 End-to-End Workflow Integration Test
"""
import unittest
import tempfile
import shutil
from pathlib import Path

from nova.agent.coding_agent import CodingAgent
from nova.permissions.permission_manager import PermissionManager
from nova.services.memory_service import MemoryService
from nova.core.config import ConfigManager


class TestDay4EndToEndWorkflow(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_root = Path(self.temp_dir) / "workspace"
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.memory_dir = Path(self.temp_dir) / "memory"

        config_path = Path(self.temp_dir) / "settings.json"
        self.config_manager = ConfigManager(config_path)
        self.config_manager.load()

        self.memory_service = MemoryService(self.config_manager, memory_dir=self.memory_dir)
        self.memory_service.initialize()

        self.permission_manager = PermissionManager(workspace_root=self.workspace_root)
        self.agent = CodingAgent(
            workspace_root=self.workspace_root,
            permission_manager=self.permission_manager,
            memory_service=self.memory_service,
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_day4_e2e_full_project_lifecycle(self):
        # 1. Create a sample Python project with requirements.txt and app.py
        req_file = self.workspace_root / "requirements.txt"
        req_file.write_text("# Day 4 Test Requirements\n", encoding="utf-8")

        app_file = self.workspace_root / "app.py"
        app_file.write_text("import sys\nimport json\nprint('NOVA DAY 4 E2E SUCCESS')\n", encoding="utf-8")

        # 2. Run Coding Agent Workflow
        result = self.agent.execute_workflow(
            task_description="Execute app.py and verify environment setup",
            user_approved_venv=True,
            user_approved_install=True,
            user_approved_run=True,
            user_approved_fix=True,
        )

        # 3. Assertions
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "COMPLETED_SUCCESS")
        self.assertIn("NOVA DAY 4 E2E SUCCESS", result["execution_result"]["stdout"])

        # 4. Verify Project State Persistence
        project_state = result["project_state"]
        self.assertIsNotNone(project_state)
        self.assertEqual(project_state["status"], "COMPLETED_SUCCESS")
        self.assertIn("environment", project_state)

        # 5. Verify Memory Store Update
        long_term = self.memory_service.get_memory("long_term.json")
        self.assertIsNotNone(long_term)
        self.assertTrue(len(long_term.get("episodes", [])) > 0)
        self.assertEqual(long_term["episodes"][-1]["task"], "Execute app.py and verify environment setup")


if __name__ == "__main__":
    unittest.main()
