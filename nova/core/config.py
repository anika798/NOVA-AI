"""
NOVA Configuration Manager
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from nova.utils.constants import DEFAULT_CONFIG_PATH, ConfigError


class ConfigManager:
    """
    Manages application configuration loading, access, and fallbacks.
    """

    _DEFAULT_CONFIG: Dict[str, Any] = {
        "app": {
            "name": "NOVA",
            "version": "1.0.0-day1",
            "mode": "Development",
            "debug": True,
        },
        "logging": {
            "level": "INFO",
            "console_output": True,
            "file_output": True,
            "log_file": "data/logs/nova.log",
            "max_bytes": 10485760,
            "backup_count": 5,
        },
        "storage": {
            "base_dir": "data",
            "memory_dir": "data/memory",
            "logs_dir": "data/logs",
        },
        "ollama": {
            "host": "localhost",
            "port": 11434,
            "model": "qwen2.5:14b",
            "timeout_seconds": 5,
        },
        "services": {
            "auto_initialize": True,
        },
    }

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path: Path = config_path or DEFAULT_CONFIG_PATH
        self._config_data: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """
        Loads settings from file. If file is missing or corrupt, uses default settings
        and writes a new valid settings file.
        """
        if not self.config_path.exists():
            self._config_data = self._DEFAULT_CONFIG.copy()
            self._save_default_config()
            return self._config_data

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if not isinstance(loaded, dict):
                    raise ConfigError(f"Invalid JSON root in {self.config_path}, expected dict.")
                self._config_data = self._merge_defaults(self._DEFAULT_CONFIG, loaded)
        except (json.JSONDecodeError, OSError) as e:
            raise ConfigError(f"Failed to parse config file {self.config_path}: {str(e)}") from e

        return self._config_data

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Retrieves a nested configuration value using dot notation (e.g. 'app.mode').
        """
        keys = key_path.split(".")
        current = self._config_data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default

        return current

    def set(self, key_path: str, value: Any) -> None:
        """
        Sets a nested configuration value using dot notation.
        """
        keys = key_path.split(".")
        current = self._config_data

        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def _save_default_config(self) -> None:
        """Writes current config memory state back to disk."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._DEFAULT_CONFIG, f, indent=2)
        except OSError as e:
            raise ConfigError(f"Could not save default config to {self.config_path}: {e}") from e

    def _merge_defaults(self, defaults: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merges user config into default dictionary."""
        result = defaults.copy()
        for k, v in user.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._merge_defaults(result[k], v)
            else:
                result[k] = v
        return result
