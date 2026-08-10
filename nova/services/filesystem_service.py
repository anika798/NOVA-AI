"""
NOVA File System Verification & Auto-Creation Service
"""
import logging
from pathlib import Path
from typing import List, Dict, Any

from nova.core.base_service import BaseService, ServiceStatus
from nova.core.config import ConfigManager
from nova.utils.constants import CONFIG_DIR, DATA_DIR, MEMORY_DIR, SESSIONS_DIR, LOGS_DIR, FileSystemError

logger = logging.getLogger("NOVA.FileSystemService")


class FileSystemService(BaseService):
    """
    Verifies workspace directory structure, creates missing paths, and ensures directory writeability.
    """

    def __init__(self, config_manager: ConfigManager):
        super().__init__(name="FileSystemService", description="Manages directory paths and workspace integrity")
        self.config_manager = config_manager
        self.required_directories: List[Path] = [
            CONFIG_DIR,
            DATA_DIR,
            MEMORY_DIR,
            SESSIONS_DIR,
            LOGS_DIR,
        ]

    def initialize(self) -> bool:
        self._set_status(ServiceStatus.INITIALIZING, "Verifying workspace folders")
        created_paths: List[str] = []
        verified_paths: List[str] = []

        try:
            for directory in self.required_directories:
                if not directory.exists():
                    logger.info(f"Creating missing directory: {directory}")
                    directory.mkdir(parents=True, exist_ok=True)
                    created_paths.append(str(directory))
                else:
                    verified_paths.append(str(directory))

                # Verify write permission by attempting to write temporary check file
                test_file = directory / ".perm_check"
                try:
                    test_file.touch()
                    test_file.unlink()
                except OSError as e:
                    raise FileSystemError(f"Directory {directory} is not writeable: {e}")

            details = {
                "created_directories": created_paths,
                "verified_directories": verified_paths,
                "total_verified": len(self.required_directories),
            }

            self._set_status(
                ServiceStatus.HEALTHY,
                f"Verified {len(self.required_directories)} system directories",
                details=details,
            )
            return True

        except Exception as e:
            logger.error(f"FileSystemService initialization failed: {e}")
            self._set_status(
                ServiceStatus.FAILED,
                f"FileSystem verification failed: {e}",
                details={"error": str(e)},
            )
            return False

    def shutdown(self) -> None:
        self._set_status(ServiceStatus.SHUTDOWN, "FileSystemService stopped")

    def is_safe_path(self, target_path: Any, root_dir: Any = None) -> bool:
        """
        Verifies whether target_path stays within root directory boundaries.
        Preventing path traversal attacks like '../secret.txt'.
        """
        from nova.permissions.permission_manager import PermissionManager
        pm = PermissionManager(workspace_root=root_dir or DATA_DIR.parent)
        return pm.is_safe_path(target_path)

