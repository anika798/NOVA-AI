"""
NOVA Project State Manager Subsystem
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from nova.utils.constants import MEMORY_DIR, NovaException

logger = logging.getLogger("NOVA.ProjectStateManager")


class ProjectStateManager:
    """
    Tracks and persists current workspace task, active environment, dependencies,
    modified files, execution telemetry, and debugging iteration state to JSON storage.
    """

    def __init__(self, workspace_root: Optional[Union[str, Path]] = None, state_file: Optional[Path] = None):
        self.workspace_root: Path = Path(workspace_root or Path.cwd()).resolve()
        self.state_file: Path = state_file or (MEMORY_DIR / "project_state.json")
        self._state: Dict[str, Any] = self._default_state()

    def _default_state(self) -> Dict[str, Any]:
        return {
            "version": "1.0",
            "project_path": str(self.workspace_root),
            "current_task": None,
            "status": "IDLE",
            "environment": {},
            "dependencies": {},
            "modified_files": [],
            "last_execution": None,
            "last_test_result": None,
            "known_errors": [],
            "debug_attempts": 0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def update_task(self, task_description: str, status: str = "IN_PROGRESS") -> None:
        """Sets active project task description and status."""
        self._state["current_task"] = task_description
        self._state["status"] = status
        self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def update_environment(self, env_info: Dict[str, Any]) -> None:
        """Updates environment state telemetry."""
        self._state["environment"] = env_info
        self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def update_dependencies(self, dep_info: Dict[str, Any]) -> None:
        """Updates dependency state telemetry."""
        self._state["dependencies"] = dep_info
        self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def record_modified_file(self, file_path: str) -> None:
        """Appends file_path to list of modified workspace files."""
        if file_path not in self._state["modified_files"]:
            self._state["modified_files"].append(file_path)
            self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
            self.save_state()

    def record_execution(self, exec_result: Dict[str, Any]) -> None:
        """Records last project run result."""
        self._state["last_execution"] = exec_result
        self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def record_test_result(self, test_result: Dict[str, Any]) -> None:
        """Records last test suite execution result."""
        self._state["last_test_result"] = test_result
        self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def record_error(self, error_analysis: Dict[str, Any]) -> None:
        """Appends error analysis to known_errors list."""
        self._state["known_errors"].append(error_analysis)
        self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def set_debug_attempts(self, attempts: int) -> None:
        """Updates current debugging attempt counter."""
        self._state["debug_attempts"] = attempts
        self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def increment_debug_attempts(self) -> int:
        """Increments and returns debugging attempt counter."""
        count = self._state.get("debug_attempts", 0) + 1
        self._state["debug_attempts"] = count
        self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.save_state()
        return count

    def reset_debug_attempts(self) -> None:
        """Resets debug attempts counter to 0."""
        self._state["debug_attempts"] = 0
        self._state["last_updated"] = datetime.now(timezone.utc).isoformat()
        self.save_state()

    def get_state(self) -> Dict[str, Any]:
        """Returns current in-memory state dictionary."""
        return self._state.copy()

    def save_state(self) -> bool:
        """Saves state dictionary to local JSON storage."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
            return True
        except OSError as e:
            logger.error(f"Failed to write project state to {self.state_file}: {e}")
            return False

    def load_state(self) -> bool:
        """Loads state dictionary from local JSON file."""
        if not self.state_file.exists():
            self._state = self._default_state()
            return False
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._state = loaded
                    return True
        except Exception as e:
            logger.error(f"Failed to parse project state file {self.state_file}: {e}")
        self._state = self._default_state()
        return False
