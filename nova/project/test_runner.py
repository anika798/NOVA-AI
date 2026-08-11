"""
NOVA Test Execution Subsystem
"""
import re
import time
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

from nova.environment.environment_manager import EnvironmentManager
from nova.permissions.permission_manager import PermissionManager
from nova.utils.constants import NovaException

logger = logging.getLogger("NOVA.TestRunner")


class TestRunnerError(NovaException):
    """Raised when test discovery or execution fails."""
    pass


class TestRunner:
    """
    Discovers and executes Python unit test suites (unittest/pytest) inside active environments,
    parsing results into structured telemetry metrics.
    """

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

    def detect_test_framework(self) -> Dict[str, Any]:
        """
        Detects available test framework and test directories in workspace.
        """
        has_tests_dir = (self.workspace_root / "tests").is_dir()
        test_files = list(self.workspace_root.glob("**/test_*.py")) + list(self.workspace_root.glob("**/*_test.py"))

        python_exec = self.environment_manager.get_python_executable()
        has_pytest = False
        try:
            res = subprocess.run([python_exec, "-c", "import pytest"], capture_output=True, timeout=5)
            has_pytest = (res.returncode == 0)
        except Exception:
            has_pytest = False

        preferred = "pytest" if has_pytest else "unittest"
        return {
            "has_tests": bool(has_tests_dir or test_files),
            "test_dir": str(self.workspace_root / "tests") if has_tests_dir else None,
            "test_file_count": len(test_files),
            "has_pytest": has_pytest,
            "preferred_framework": preferred,
        }

    def run_tests(
        self,
        test_dir: str = "tests",
        pattern: str = "test_*.py",
        framework: Optional[str] = None,
        timeout_seconds: int = 60,
    ) -> Dict[str, Any]:
        """
        Executes test suite using active environment python executable.
        """
        detection = self.detect_test_framework()
        fw = framework or detection["preferred_framework"]
        python_exec = self.environment_manager.get_python_executable()

        if fw == "pytest" and detection["has_pytest"]:
            cmd_list = [python_exec, "-m", "pytest", test_dir]
        else:
            # Fallback to standard library unittest
            cmd_list = [python_exec, "-m", "unittest", "discover", "-s", test_dir, "-p", pattern]

        cmd_str = " ".join(cmd_list)
        logger.info(f"Running test suite via '{cmd_str}'...")

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
            combined_output = (res.stdout or "") + "\n" + (res.stderr or "")

            parsed = self._parse_test_output(combined_output, res.returncode)

            return {
                "success": (res.returncode == 0),
                "framework": fw,
                "command": cmd_str,
                "exit_code": res.returncode,
                "execution_time_ms": round(elapsed_ms, 2),
                "total_tests": parsed["total"],
                "passed": parsed["passed"],
                "failed": parsed["failed"],
                "skipped": parsed["skipped"],
                "errors": parsed["errors"],
                "stdout": res.stdout,
                "stderr": res.stderr,
            }

        except subprocess.TimeoutExpired as e:
            elapsed_ms = (time.time() - start_time) * 1000.0
            return {
                "success": False,
                "framework": fw,
                "command": cmd_str,
                "exit_code": -1,
                "execution_time_ms": round(elapsed_ms, 2),
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 1,
                "stdout": e.stdout or "",
                "stderr": f"Test execution timed out after {timeout_seconds} seconds.",
            }
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000.0
            return {
                "success": False,
                "framework": fw,
                "command": cmd_str,
                "exit_code": -1,
                "execution_time_ms": round(elapsed_ms, 2),
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 1,
                "stdout": "",
                "stderr": str(e),
            }

    def _parse_test_output(self, output: str, exit_code: int) -> Dict[str, int]:
        """Parses output text for unittest/pytest count metrics."""
        total = 0
        passed = 0
        failed = 0
        skipped = 0
        errors = 0

        # Unittest match: "Ran X tests in Ys"
        ran_match = re.search(r"Ran\s+(\d+)\s+tests?", output)
        if ran_match:
            total = int(ran_match.group(1))
            if exit_code == 0:
                passed = total
            else:
                fail_match = re.search(r"failures=(\d+)", output)
                err_match = re.search(r"errors=(\d+)", output)
                skip_match = re.search(r"skipped=(\d+)", output)

                failed = int(fail_match.group(1)) if fail_match else 0
                errors = int(err_match.group(1)) if err_match else 0
                skipped = int(skip_match.group(1)) if skip_match else 0
                passed = max(0, total - (failed + errors + skipped))

        # Pytest match: "X passed, Y failed in Zs"
        elif "passed" in output or "failed" in output:
            p_match = re.search(r"(\d+)\s+passed", output)
            f_match = re.search(r"(\d+)\s+failed", output)
            s_match = re.search(r"(\d+)\s+skipped", output)
            e_match = re.search(r"(\d+)\s+error", output)

            passed = int(p_match.group(1)) if p_match else 0
            failed = int(f_match.group(1)) if f_match else 0
            skipped = int(s_match.group(1)) if s_match else 0
            errors = int(e_match.group(1)) if e_match else 0
            total = passed + failed + skipped + errors

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
        }
