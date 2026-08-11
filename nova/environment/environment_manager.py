"""
NOVA Environment Manager Subsystem
"""
import sys
import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

from nova.permissions.permission_manager import PermissionManager, PermissionLevel
from nova.utils.constants import NovaException

logger = logging.getLogger("NOVA.EnvironmentManager")


class EnvironmentError(NovaException):
    """Raised when environment detection or creation fails."""
    pass


class EnvironmentManager:
    """
    Detects, verifies, and creates isolated runtime execution environments (e.g. Python venv).
    Routes all state-changing creation operations through PermissionManager.
    """

    VENV_CANDIDATES: List[str] = [".venv", "venv", "env", "ENV"]

    def __init__(self, workspace_root: Optional[Union[str, Path]] = None, permission_manager: Optional[PermissionManager] = None):
        self.workspace_root: Path = Path(workspace_root or Path.cwd()).resolve()
        self.permission_manager: PermissionManager = permission_manager or PermissionManager(workspace_root=self.workspace_root)
        self._active_env_path: Optional[Path] = None
        self._active_python_exec: Optional[Path] = None

    def detect_language(self) -> Dict[str, Any]:
        """
        Detects primary programming language based on workspace files.
        """
        languages = []
        if any(self.workspace_root.glob("*.py")) or (self.workspace_root / "requirements.txt").exists() or (self.workspace_root / "pyproject.toml").exists():
            languages.append("Python")
        if (self.workspace_root / "package.json").exists() or any(self.workspace_root.glob("*.js")) or any(self.workspace_root.glob("*.ts")):
            languages.append("Node.js")
        if (self.workspace_root / "pom.xml").exists() or (self.workspace_root / "build.gradle").exists() or any(self.workspace_root.glob("*.java")):
            languages.append("Java")

        primary = languages[0] if languages else "Python"
        return {
            "primary": primary,
            "detected": languages,
        }

    def detect_python_environment(self) -> Dict[str, Any]:
        """
        Scans workspace root for Python executables, version, and virtual environments.
        """
        venv_found: Optional[Path] = None
        for candidate in self.VENV_CANDIDATES:
            venv_path = self.workspace_root / candidate
            if venv_path.is_dir() and (venv_path / "pyvenv.cfg").exists():
                venv_found = venv_path
                break

        python_exec = self._get_python_executable(venv_found)
        version_str = self._get_python_version(python_exec)

        self._active_env_path = venv_found
        self._active_python_exec = python_exec

        return {
            "workspace_root": str(self.workspace_root),
            "venv_found": bool(venv_found),
            "venv_path": str(venv_found) if venv_found else None,
            "python_executable": str(python_exec) if python_exec else sys.executable,
            "python_version": version_str,
            "is_virtual_env": bool(venv_found or sys.prefix != sys.base_prefix),
        }

    def create_virtual_environment(self, venv_name: str = ".venv", user_approved: bool = False) -> Dict[str, Any]:
        """
        Proposes and creates a Python virtual environment inside workspace root.
        Requires permission approval before execution.
        """
        target_path = (self.workspace_root / venv_name).resolve()

        # Security check: target path must be safe inside workspace
        if not self.permission_manager.is_safe_path(target_path):
            raise EnvironmentError(f"Target environment path '{target_path}' escapes workspace boundary.")

        cmd = f"{sys.executable} -m venv {venv_name}"
        perm_level = self.permission_manager.check_command_permission(cmd)

        if perm_level == PermissionLevel.BLOCKED:
            return {
                "success": False,
                "error": "Virtual environment creation is BLOCKED by security policy.",
                "created": False,
            }

        if perm_level == PermissionLevel.CONFIRM and not user_approved:
            return {
                "success": False,
                "permission_required": True,
                "proposed_action": {
                    "tool": "EnvironmentManager.create_virtual_environment",
                    "command": cmd,
                    "target_path": str(target_path),
                    "reason": f"Create Python virtual environment in '{venv_name}' for isolated package installation.",
                },
                "created": False,
            }

        # Execute venv creation
        try:
            logger.info(f"Creating virtual environment at '{target_path}'...")
            res = subprocess.run(
                [sys.executable, "-m", "venv", str(target_path)],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
            )

            # Verify python executable in created venv
            python_exec = self._get_python_executable(target_path)
            if not python_exec or not python_exec.exists():
                raise EnvironmentError(f"Venv created at {target_path} but Python executable not found.")

            self._active_env_path = target_path
            self._active_python_exec = python_exec

            logger.info(f"Successfully created virtual environment at '{target_path}'")
            return {
                "success": True,
                "created": True,
                "venv_path": str(target_path),
                "python_executable": str(python_exec),
                "stdout": res.stdout,
                "stderr": res.stderr,
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create virtual environment: {e.stderr}")
            return {
                "success": False,
                "created": False,
                "error": f"venv creation failed with exit code {e.returncode}: {e.stderr}",
            }
        except Exception as e:
            logger.error(f"Error creating virtual environment: {e}")
            return {
                "success": False,
                "created": False,
                "error": str(e),
            }

    def health_check(self) -> Dict[str, Any]:
        """
        Executes complete environment health verification check.
        """
        info = self.detect_python_environment()
        python_exec = info.get("python_executable", sys.executable)

        # Test pip availability
        pip_available = False
        pip_version = "Unavailable"
        try:
            res = subprocess.run(
                [python_exec, "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if res.returncode == 0:
                pip_available = True
                pip_version = res.stdout.strip().splitlines()[0] if res.stdout else "Available"
        except Exception:
            pip_available = False

        status = "Healthy" if info.get("is_virtual_env") and pip_available else ("Degraded" if pip_available else "Missing")

        return {
            "status": status,
            "language": self.detect_language()["primary"],
            "python_executable": python_exec,
            "python_version": info.get("python_version", "Unknown"),
            "virtual_environment": info.get("venv_path") or ("Active" if info.get("is_virtual_env") else "None"),
            "pip_available": pip_available,
            "pip_version": pip_version,
            "details": info,
        }

    def get_environment_info(self) -> Dict[str, Any]:
        """Returns structured environment telemetry dict."""
        return self.health_check()

    def get_python_executable(self) -> str:
        """Returns path string to the active Python executable."""
        if self._active_python_exec and self._active_python_exec.exists():
            return str(self._active_python_exec)

        info = self.detect_python_environment()
        return info.get("python_executable", sys.executable)

    def _get_python_executable(self, venv_path: Optional[Path]) -> Optional[Path]:
        if venv_path and venv_path.exists():
            if os.name == "nt":
                exec_path = venv_path / "Scripts" / "python.exe"
            else:
                exec_path = venv_path / "bin" / "python"
            if exec_path.exists():
                return exec_path

        return Path(sys.executable)

    def _get_python_version(self, python_exec: Optional[Path]) -> str:
        if not python_exec or not python_exec.exists():
            return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        try:
            res = subprocess.run(
                [str(python_exec), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0:
                return res.stdout.strip().replace("Python ", "")
        except Exception:
            pass
        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
