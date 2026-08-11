"""
NOVA Dependency Manager Subsystem
"""
import re
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Union

from nova.environment.environment_manager import EnvironmentManager
from nova.permissions.permission_manager import PermissionManager, PermissionLevel
from nova.utils.constants import NovaException

logger = logging.getLogger("NOVA.DependencyManager")


class DependencyError(NovaException):
    """Raised when dependency detection, parsing, or installation fails."""
    pass


class DependencyManager:
    """
    Detects, parses, verifies, and installs project dependencies inside isolated environments.
    Enforces permission authorization for package installation.
    """

    SUPPORTED_FILES: Dict[str, str] = {
        "requirements.txt": "python",
        "pyproject.toml": "python",
        "Pipfile": "python",
        "package.json": "node",
        "pom.xml": "java",
        "build.gradle": "java",
    }

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

    def detect_dependency_files(self) -> Dict[str, Any]:
        """
        Scans workspace root for supported dependency manifest files.
        """
        found_files = []
        for filename in self.SUPPORTED_FILES.keys():
            file_path = self.workspace_root / filename
            if file_path.is_file():
                found_files.append(filename)

        return {
            "workspace_root": str(self.workspace_root),
            "files_found": found_files,
            "has_python_deps": any(f in ["requirements.txt", "pyproject.toml", "Pipfile"] for f in found_files),
        }

    def parse_python_requirements(self, filename: str = "requirements.txt") -> List[str]:
        """
        Parses package names from requirements.txt file.
        """
        file_path = self.workspace_root / filename
        if not file_path.is_file():
            return []

        packages = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("-"):
                        continue
                    # Normalize specifiers (e.g. requests>=2.0 -> requests)
                    pkg_name = re.split(r"[~=><!;\s]", line)[0].strip()
                    if pkg_name:
                        packages.append(pkg_name)
        except OSError as e:
            logger.error(f"Error reading {filename}: {e}")
        return list(dict.fromkeys(packages))  # Deduplicate keeping order

    def parse_pyproject_toml(self, filename: str = "pyproject.toml") -> List[str]:
        """
        Parses dependencies from pyproject.toml file.
        """
        file_path = self.workspace_root / filename
        if not file_path.is_file():
            return []

        packages = []
        try:
            content = file_path.read_text(encoding="utf-8")
            # Simple regex search for dependencies list in pyproject.toml
            deps_match = re.search(r"dependencies\s*=\s*\[(.*?)\]", content, re.DOTALL)
            if deps_match:
                deps_str = deps_match.group(1)
                for item in re.findall(r"[\"']([^\"']+)[\"']", deps_str):
                    pkg_name = re.split(r"[~=><!;\s]", item)[0].strip()
                    if pkg_name:
                        packages.append(pkg_name)
        except Exception as e:
            logger.error(f"Error parsing {filename}: {e}")
        return list(dict.fromkeys(packages))

    def get_declared_dependencies(self) -> List[str]:
        """
        Aggregates all declared Python dependencies across requirements.txt and pyproject.toml.
        """
        reqs = self.parse_python_requirements("requirements.txt")
        pyproject_reqs = self.parse_pyproject_toml("pyproject.toml")
        combined = list(dict.fromkeys(reqs + pyproject_reqs))
        return combined

    def get_installed_packages(self) -> Dict[str, str]:
        """
        Executes pip list --format=json inside active environment to get installed packages.
        """
        python_exec = self.environment_manager.get_python_executable()
        installed: Dict[str, str] = {}
        try:
            res = subprocess.run(
                [python_exec, "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                for item in data:
                    name = item.get("name", "").strip().lower()
                    version = item.get("version", "").strip()
                    if name:
                        installed[name] = version
        except Exception as e:
            logger.error(f"Failed to query installed packages: {e}")
        return installed

    def check_missing_dependencies(self) -> Dict[str, Any]:
        """
        Compares declared dependencies against currently installed packages.
        """
        declared = self.get_declared_dependencies()
        installed_map = self.get_installed_packages()

        missing = []
        available = []

        for pkg in declared:
            pkg_lower = pkg.lower().replace("-", "_")
            installed_keys = [k.replace("-", "_") for k in installed_map.keys()]
            if pkg.lower() in installed_map or pkg_lower in installed_keys:
                available.append(pkg)
            else:
                missing.append(pkg)

        return {
            "declared_count": len(declared),
            "available_count": len(available),
            "missing_count": len(missing),
            "declared": declared,
            "available": available,
            "missing": missing,
        }

    def install_dependency(self, package_name: str, user_approved: bool = False) -> Dict[str, Any]:
        """
        Installs target package into active virtual environment.
        Enforces permission authorization before execution.
        """
        if not package_name or not package_name.strip():
            return {"success": False, "error": "Package name cannot be empty."}

        pkg_clean = package_name.strip()
        python_exec = self.environment_manager.get_python_executable()

        cmd = f"{python_exec} -m pip install {pkg_clean}"
        perm_level = self.permission_manager.check_command_permission(cmd)

        if perm_level == PermissionLevel.BLOCKED:
            return {
                "success": False,
                "error": f"Installing package '{pkg_clean}' is BLOCKED by security policy.",
                "installed": False,
            }

        if perm_level == PermissionLevel.CONFIRM and not user_approved:
            return {
                "success": False,
                "permission_required": True,
                "proposed_action": {
                    "tool": "DependencyManager.install_dependency",
                    "command": cmd,
                    "package": pkg_clean,
                    "environment_python": python_exec,
                    "reason": f"Install missing Python package '{pkg_clean}' into active environment.",
                },
                "installed": False,
            }

        try:
            logger.info(f"Installing package '{pkg_clean}' via '{python_exec}'...")
            res = subprocess.run(
                [python_exec, "-m", "pip", "install", pkg_clean],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=180,
            )

            success = (res.returncode == 0)
            verified = self.verify_installation(pkg_clean) if success else False

            return {
                "success": success and verified,
                "installed": success and verified,
                "package": pkg_clean,
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "verified": verified,
            }

        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "installed": False,
                "package": pkg_clean,
                "error": f"pip install failed with exit code {e.returncode}: {e.stderr}",
            }
        except Exception as e:
            return {
                "success": False,
                "installed": False,
                "package": pkg_clean,
                "error": str(e),
            }

    def verify_installation(self, package_name: str) -> bool:
        """
        Verifies if package is listed in pip list or importable.
        """
        pkg_lower = package_name.strip().lower().replace("-", "_")
        installed_map = self.get_installed_packages()
        installed_keys = [k.replace("-", "_") for k in installed_map.keys()]

        if pkg_lower in [k.lower() for k in installed_map.keys()] or pkg_lower in installed_keys:
            return True

        # Try import check via python -c
        python_exec = self.environment_manager.get_python_executable()
        try:
            res = subprocess.run(
                [python_exec, "-c", f"import {pkg_lower}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return res.returncode == 0
        except Exception:
            return False
