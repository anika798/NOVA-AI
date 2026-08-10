"""
NOVA Permission Manager Module
"""
import logging
from enum import Enum
from pathlib import Path
from typing import Union, List, Optional, Dict, Any

logger = logging.getLogger("NOVA.PermissionManager")


class PermissionLevel(str, Enum):
    SAFE = "SAFE"
    CONFIRM = "CONFIRM"
    BLOCKED = "BLOCKED"


class PermissionManager:
    """
    Manages security permissions, action risk classification,
    and path restriction boundaries.
    """

    BLOCKED_COMMAND_PATTERNS: List[str] = [
        "rm -rf /",
        "rm -rf /*",
        "rm -rf c:\\",
        "rm -rf c:/",
        "format ",
        "del /s /q c:\\",
        "del /f /s /q c:\\windows",
        "chmod 777 /",
        "dd if=",
        ":(){ :|:& };:",
        "shutdown",
        "reboot",
        "mkfs",
    ]

    SAFE_COMMAND_PATTERNS: List[str] = [
        "git status",
        "git branch",
        "git log",
        "ls",
        "dir",
        "pwd",
        "echo",
        "python --version",
        "node --version",
        "pip --version",
    ]

    def __init__(self, workspace_root: Optional[Union[str, Path]] = None):
        self.workspace_root: Path = Path(workspace_root or Path.cwd()).resolve()

    def check_command_permission(self, command: str) -> PermissionLevel:
        """
        Classifies a shell/terminal command into SAFE, CONFIRM, or BLOCKED.
        """
        if not command or not command.strip():
            return PermissionLevel.SAFE

        cmd_clean = command.strip().lower()

        # Check for blocked dangerous commands
        for pattern in self.BLOCKED_COMMAND_PATTERNS:
            if pattern.lower() in cmd_clean:
                logger.warning(f"Blocked dangerous command pattern matched: '{pattern}' in '{command}'")
                return PermissionLevel.BLOCKED

        # Check for safe read-only commands
        for pattern in self.SAFE_COMMAND_PATTERNS:
            if cmd_clean == pattern.lower() or cmd_clean.startswith(pattern.lower() + " "):
                return PermissionLevel.SAFE

        # Default actions require user confirmation
        return PermissionLevel.CONFIRM

    def is_safe_path(self, target_path: Union[str, Path], root_override: Optional[Union[str, Path]] = None) -> bool:
        """
        Validates whether target_path remains strictly inside the permitted workspace directory,
        preventing path traversal (e.g. '../secret.txt') and unauthorized absolute paths.
        """
        base = Path(root_override or self.workspace_root).resolve()
        try:
            path_obj = Path(target_path)
            if not path_obj.is_absolute():
                resolved = (base / path_obj).resolve()
            else:
                resolved = path_obj.resolve()

            # Ensure resolved path starts with base path
            resolved.relative_to(base)
            return True
        except (ValueError, Exception):
            return False
