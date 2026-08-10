"""
NOVA Memory Storage Service
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from nova.core.base_service import BaseService, ServiceStatus
from nova.core.config import ConfigManager
from nova.utils.constants import MEMORY_DIR, DEFAULT_MEMORY_SCHEMAS, MemoryError

logger = logging.getLogger("NOVA.MemoryService")


class MemoryService(BaseService):
    """
    Manages persistent JSON memory stores for short-term context, long-term knowledge,
    user profile settings, and system execution state.
    """

    def __init__(self, config_manager: ConfigManager, memory_dir: Optional[Path] = None):
        super().__init__(name="MemoryService", description="Manages persistent JSON memory architecture")
        self.config_manager = config_manager
        self.memory_dir: Path = memory_dir or MEMORY_DIR
        self._memory_files: Dict[str, Path] = {}
        self._loaded_memories: Dict[str, Dict[str, Any]] = {}

    def initialize(self) -> bool:
        self._set_status(ServiceStatus.INITIALIZING, "Initializing memory stores")

        try:
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            files_created: List[str] = []
            files_verified: List[str] = []
            file_stats: Dict[str, Dict[str, Any]] = {}
            total_size_bytes = 0

            for filename, default_schema in DEFAULT_MEMORY_SCHEMAS.items():
                file_path = self.memory_dir / filename
                self._memory_files[filename] = file_path

                if not file_path.exists():
                    logger.info(f"Initializing missing memory file: {filename}")
                    self._create_memory_file(file_path, default_schema)
                    files_created.append(filename)
                else:
                    logger.debug(f"Verifying existing memory file: {filename}")
                    self._validate_and_load_memory(file_path, filename, default_schema)
                    files_verified.append(filename)

                size = file_path.stat().st_size
                total_size_bytes += size
                file_stats[filename] = {
                    "exists": True,
                    "size_bytes": size,
                    "valid_json": True,
                }

            # Discover and load any existing custom memory files
            for json_file in self.memory_dir.glob("*.json"):
                fn = json_file.name
                if fn not in self._loaded_memories:
                    self._memory_files[fn] = json_file
                    self._validate_and_load_memory(json_file, fn, {})

            # Update system state file with boot timestamp
            self._update_boot_telemetry()


            details = {
                "memory_dir": str(self.memory_dir),
                "created_files": files_created,
                "verified_files": files_verified,
                "file_count": len(self._memory_files),
                "total_size_bytes": total_size_bytes,
                "total_size_kb": round(total_size_bytes / 1024, 2),
                "file_stats": file_stats,
            }

            self._set_status(
                ServiceStatus.HEALTHY,
                f"Active ({len(self._memory_files)} JSON memory files online, {details['total_size_kb']} KB)",
                details=details,
            )
            return True

        except Exception as e:
            logger.error(f"MemoryService initialization error: {e}", exc_info=True)
            self._set_status(
                ServiceStatus.FAILED,
                f"Memory initialization failed: {e}",
                details={"error": str(e)},
            )
            return False

    def get_memory(self, name: str) -> Optional[Dict[str, Any]]:
        """Returns in-memory cached content of target memory file."""
        return self._loaded_memories.get(name)

    def save_memory(self, name: str, data: Dict[str, Any]) -> bool:
        """Saves dictionary data to target memory JSON file."""
        if name not in self._memory_files:
            file_path = self.memory_dir / name
            self._memory_files[name] = file_path

        file_path = self._memory_files[name]
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self._loaded_memories[name] = data
            return True
        except OSError as e:
            logger.error(f"Failed to write memory file {name}: {e}")
            return False

    def list_memories(self) -> List[str]:
        """Returns list of all available memory store names."""
        return list(self._loaded_memories.keys())

    def delete_memory(self, name: str) -> bool:
        """Deletes target memory store from cache and local file system."""
        deleted = False
        if name in self._loaded_memories:
            del self._loaded_memories[name]
            deleted = True

        if name in self._memory_files:
            file_path = self._memory_files[name]
            del self._memory_files[name]
            if file_path.exists():
                try:
                    file_path.unlink()
                    return True
                except OSError as e:
                    logger.error(f"Failed to delete memory file {name}: {e}")
                    return False
            return True
        return deleted

    def shutdown(self) -> None:
        self._set_status(ServiceStatus.SHUTDOWN, "MemoryService stopped")


    def _create_memory_file(self, path: Path, default_data: Dict[str, Any]) -> None:
        """Creates a new memory file formatted with default JSON schema."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=2)
            self._loaded_memories[path.name] = default_data.copy()
        except OSError as e:
            raise MemoryError(f"Could not create memory file {path}: {e}") from e

    def _validate_and_load_memory(self, path: Path, filename: str, default_schema: Dict[str, Any]) -> None:
        """Validates JSON readability and structure; backs up & repairs corrupted files."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("Root element is not a JSON object")
                self._loaded_memories[filename] = data
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.warning(f"Memory file {filename} is corrupt: {e}. Re-initializing with defaults...")
            backup_path = path.with_suffix(f".corrupt.{int(datetime.now().timestamp())}.bak")
            try:
                if path.exists():
                    path.rename(backup_path)
                    logger.info(f"Backed up corrupted memory file to {backup_path}")
            except OSError as backup_err:
                logger.error(f"Could not rename corrupt memory file: {backup_err}")

            self._create_memory_file(path, default_schema)

    def _update_boot_telemetry(self) -> None:
        """Updates system_state.json with boot statistics."""
        sys_state = self._loaded_memories.get("system_state.json", {})
        boot_count = sys_state.get("boot_count", 0) + 1
        sys_state["boot_count"] = boot_count
        sys_state["last_boot"] = datetime.now(timezone.utc).isoformat()
        sys_state["health_status"] = "online"
        self.save_memory("system_state.json", sys_state)
