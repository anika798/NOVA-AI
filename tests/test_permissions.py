"""
Automated Tests for NOVA Permission Manager Subsystem
"""
import unittest
from nova.permissions.permission_manager import PermissionManager, PermissionLevel


class TestPermissionManager(unittest.TestCase):

    def setUp(self):
        self.permission_manager = PermissionManager()

    def test_allowed_safe_operations(self):
        safe_commands = [
            "git status",
            "git branch",
            "git log",
            "ls",
            "dir",
            "echo Hello World",
            "python --version",
        ]
        for cmd in safe_commands:
            perm = self.permission_manager.check_command_permission(cmd)
            self.assertEqual(perm, PermissionLevel.SAFE, f"Expected '{cmd}' to be classified as SAFE")

    def test_confirm_operations(self):
        confirm_commands = [
            "python app.py",
            "pip install fastapi",
            "git commit -m 'feat: update'",
            "touch newfile.txt",
        ]
        for cmd in confirm_commands:
            perm = self.permission_manager.check_command_permission(cmd)
            self.assertEqual(perm, PermissionLevel.CONFIRM, f"Expected '{cmd}' to be classified as CONFIRM")

    def test_dangerous_blocked_commands(self):
        # NOTE: Test MUST ONLY evaluate classification and NEVER execute commands!
        dangerous_commands = [
            "rm -rf /",
            "rm -rf /*",
            "rm -rf C:\\",
            "format C:",
            "del /s /q c:\\windows",
            ":(){ :|:& };:",
            "shutdown -h now",
        ]
        for cmd in dangerous_commands:
            perm = self.permission_manager.check_command_permission(cmd)
            self.assertEqual(perm, PermissionLevel.BLOCKED, f"Expected dangerous command '{cmd}' to be BLOCKED")


if __name__ == "__main__":
    unittest.main()
