"""
NOVA Ollama Integration & Model Health Verification Service
"""
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

from nova.core.base_service import BaseService, ServiceStatus
from nova.core.config import ConfigManager

logger = logging.getLogger("NOVA.OllamaService")


class OllamaService(BaseService):
    """
    Manages connection testing, health monitoring, and model availability checks
    for the local Ollama LLM provider.
    """

    def __init__(self, config_manager: ConfigManager):
        super().__init__(name="OllamaService", description="Manages local Ollama LLM connectivity & model verification")
        self.config_manager = config_manager
        self.host: str = config_manager.get("ollama.host", "localhost")
        self.port: int = config_manager.get("ollama.port", 11434)
        self.configured_model: str = config_manager.get("ollama.model", "qwen2.5:7b")
        self.timeout: int = config_manager.get("ollama.timeout_seconds", 5)

        self._base_url: str = f"http://{self.host}:{self.port}"
        self._available_models: List[str] = []
        self._model_found: bool = False
        self._server_reachable: bool = False
        self._server_version: Optional[str] = None

    @property
    def is_connected(self) -> bool:
        """Returns True if local Ollama daemon responds to HTTP requests."""
        return self._server_reachable

    @property
    def model_available(self) -> bool:
        """Returns True if target configured model is installed in Ollama."""
        return self._model_found

    def initialize(self) -> bool:
        self._set_status(ServiceStatus.INITIALIZING, f"Connecting to Ollama at {self._base_url}")
        logger.info(f"Checking Ollama connectivity at {self._base_url} (Target model: {self.configured_model})...")

        # 1. Test basic server connectivity & version
        self._server_reachable, self._server_version = self._check_version()

        if not self._server_reachable:
            msg = f"Ollama daemon unreachable at {self._base_url}"
            logger.warning(f"{msg}. Ensure Ollama is running (`ollama serve`).")
            self._set_status(
                ServiceStatus.FAILED,
                msg,
                details={
                    "base_url": self._base_url,
                    "connected": False,
                    "model_configured": self.configured_model,
                    "model_available": False,
                    "available_models": [],
                    "remedy": f"Start local Ollama server: `ollama serve`",
                },
            )
            return False

        # 2. Fetch list of installed models
        self._available_models = self._fetch_tags()
        self._model_found = self._verify_model_presence(self.configured_model, self._available_models)

        details = {
            "base_url": self._base_url,
            "connected": True,
            "version": self._server_version,
            "model_configured": self.configured_model,
            "model_available": self._model_found,
            "available_models": self._available_models,
        }

        if self._model_found:
            msg = f"Connected ({self.configured_model} online)"
            logger.info(f"Ollama server verified. Target model '{self.configured_model}' is ready.")
            self._set_status(ServiceStatus.HEALTHY, msg, details=details)
            return True
        else:
            msg = f"Ollama online, but model '{self.configured_model}' not found"
            logger.warning(f"{msg}. Installed models: {self._available_models}")
            details["remedy"] = f"Run `ollama pull {self.configured_model}` to download model"
            self._set_status(ServiceStatus.DEGRADED, msg, details=details)
            return False

    def shutdown(self) -> None:
        self._set_status(ServiceStatus.SHUTDOWN, "OllamaService stopped")

    def _check_version(self) -> tuple[bool, Optional[str]]:
        """Queries Ollama /api/version endpoint."""
        url = f"{self._base_url}/api/version"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NOVA-Bootstrap/1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return True, data.get("version", "unknown")
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            logger.debug(f"Ollama version check failed: {e}")
        return False, None

    def _fetch_tags(self) -> List[str]:
        """Queries Ollama /api/tags endpoint for available model names."""
        url = f"{self._base_url}/api/tags"
        models: List[str] = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "NOVA-Bootstrap/1.0"})
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    model_objs = data.get("models", [])
                    for m in model_objs:
                        name = m.get("name")
                        if name:
                            models.append(name)
        except Exception as e:
            logger.error(f"Failed to query Ollama model list: {e}")
        return models

    def _verify_model_presence(self, target_model: str, available_models: List[str]) -> bool:
        """Checks if target model is present, accounting for tag variations (e.g. qwen2.5:14b vs qwen2.5:14b-instruct)."""
        target_lower = target_model.lower()

        for model_name in available_models:
            name_lower = model_name.lower()
            if name_lower == target_lower:
                return True
            # Also match if target without default tag matches (e.g. 'qwen2.5:14b' vs 'qwen2.5:14b-latest')
            if target_lower.split(":")[0] in name_lower and target_lower.split(":")[-1] in name_lower:
                return True

        return False
