"""
NOVA Project Execution Runner Subsystem
"""
import sys
import time
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

from nova.environment.environment_manager import EnvironmentManager
from nova.permissions.permission_manager import PermissionManager, PermissionLevel
from nova.utils.constants import NovaException

logger = logging.getLogger("NOVA.ProjectRunner")


class ProjectRunnerError(NovaException):
    """Raised when project entry point discovery or execution fails."""
    pass


class ProjectRunner:
    """
    Discovers main project entry points and safely executes application scripts
    within active virtual environments, subject to PermissionManager approval.
    """

    DEFAULT_ENTRY_POINTS: List[str] = [
        "main.py",
        "app.py",
        "run.py",
        "__main__.py",
        "index.py",
        "cli.py",
        "src/main.py",
        "src/app.py",
    ]

    def __init__(
        self,
        workspace_root: Optional[Union[str, Path]] = None,
        environment_manager: Optional[EnvironmentManager] = None,
        permission_manager: Optional[PermissionManager] = None,
    ):
        self.workspace_root: Path = Path(workspace_root or Path.cwd()).resolve()
        self.environment_manager: EnvironmentManager = environment_manager or EnvironmentManager(workspace_root=self.workspace_root)
        self.permission_manager: PermissionManager = permission_manager or getattr(
            self.environment_manager, "permission_manager", PermissionManager(workspace_root=self.workspace_root)
        )

    def find_entry_point(self, preferred: Optional[str] = None) -> Optional[Path]:
        """
        Discovers project entry point script.
        """
        if preferred:
            pref_path = (self.workspace_root / preferred).resolve()
            if pref_path.is_file():
                return pref_path

        for candidate in self.DEFAULT_ENTRY_POINTS:
            cand_path = (self.workspace_root / candidate).resolve()
            if cand_path.is_file():
                return cand_path

        # Check for any .py file in workspace root if no default candidate matched
        py_files = list(self.workspace_root.glob("*.py"))
        if py_files:
            return py_files[0].resolve()

        return None

    def run_project(
        self,
        entry_point: Optional[str] = None,
        args: Optional[List[str]] = None,
        timeout_seconds: int = 30,
        user_approved: bool = False,
    ) -> Dict[str, Any]:
        """
        Runs candidate entry point using environment Python executable.
        Enforces permission approval before starting execution.
        """
        ep = self.find_entry_point(entry_point)
        if not ep or not ep.is_file():
            return {
                "success": False,
                "error": f"No valid Python entry point found in {self.workspace_root}",
                "exit_code": -1,
                "stdout": "",
                "stderr": "Entry point missing",
                "execution_time_ms": 0.0,
                "process_status": "FAILED",
            }

        # Check path security
        if not self.permission_manager.is_safe_path(ep):
            return {
                "success": False,
                "error": f"Entry point path '{ep}' escapes workspace security boundary.",
                "exit_code": -1,
                "stdout": "",
                "stderr": "Security error: Path boundary escape",
                "execution_time_ms": 0.0,
                "process_status": "BLOCKED",
            }

        rel_entry = ep.relative_to(self.workspace_root)
        python_exec = self.environment_manager.get_python_executable()

        cmd_list = [python_exec, str(ep)] + (args or [])
        cmd_str = " ".join(cmd_list)

        perm_level = self.permission_manager.check_command_permission(cmd_str)

        if perm_level == PermissionLevel.BLOCKED:
            return {
                "success": False,
                "error": f"Execution of command '{cmd_str}' is BLOCKED by security policy.",
                "exit_code": -1,
                "stdout": "",
                "stderr": "Security error: Command BLOCKED",
                "execution_time_ms": 0.0,
                "process_status": "BLOCKED",
            }

        if perm_level == PermissionLevel.CONFIRM and not user_approved:
            return {
                "success": False,
                "permission_required": True,
                "proposed_action": {
                    "tool": "ProjectRunner.run_project",
                    "command": cmd_str,
                    "entry_point": str(rel_entry),
                    "python_executable": python_exec,
                    "reason": f"Execute Python application entry point '{rel_entry}'.",
                },
                "process_status": "WAITING_FOR_PERMISSION",
            }

        logger.info(f"Executing project entry point '{rel_entry}' with '{python_exec}'...")
        start_time = time.time()
        try:
            res = subprocess.run(
                cmd_list,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            elapsed_ms = (time.time() - start_time) * 1000.0

            success = (res.returncode == 0)
            status = "COMPLETED_SUCCESS" if success else "COMPLETED_FAILURE"

            return {
                "success": success,
                "entry_point": str(rel_entry),
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "execution_time_ms": round(elapsed_ms, 2),
                "process_status": status,
            }

        except subprocess.TimeoutExpired as e:
            elapsed_ms = (time.time() - start_time) * 1000.0
            return {
                "success": False,
                "entry_point": str(rel_entry),
                "exit_code": -1,
                "stdout": e.stdout or "",
                "stderr": f"Process execution timed out after {timeout_seconds} seconds.",
                "execution_time_ms": round(elapsed_ms, 2),
                "process_status": "TIMEOUT",
            }
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000.0
            return {
                "success": False,
                "entry_point": str(rel_entry),
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "execution_time_ms": round(elapsed_ms, 2),
                "process_status": "ERROR",
            }
