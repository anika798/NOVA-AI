"""
NOVA Bootstrap & Application Initialization Core
"""
import sys
import logging
from typing import Optional, Dict, Any

from nova.core.config import ConfigManager
from nova.core.logger import LoggerManager
from nova.core.service_manager import ServiceManager
from nova.services.filesystem_service import FileSystemService
from nova.services.memory_service import MemoryService
from nova.services.ollama_service import OllamaService
from nova.ai.engine import AIEngineService
from nova.banner import StartupBanner
from nova.utils.constants import NovaException, DEFAULT_CONFIG_PATH, DEFAULT_LOG_PATH, LOGS_DIR

logger = logging.getLogger("NOVA.Bootstrap")


class ApplicationBootstrap:
    """
    Orchestrates application initialization, service registration, health checks,
    and startup telemetry display.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config_manager: Optional[ConfigManager] = None
        self.service_manager: Optional[ServiceManager] = None
        self.ai_engine: Optional[AIEngineService] = None
        self.is_initialized: bool = False

    def initialize(self) -> bool:
        """
        Executes complete bootstrap sequence.
        Returns True if initialization completed cleanly, False otherwise.
        """
        try:
            # Step 1: Configuration Initialization
            self.config_manager = ConfigManager(self.config_path)
            config_data = self.config_manager.load()

            # Step 2: Logging System Setup
            log_level = self.config_manager.get("logging.level", "INFO")
            log_path = LOGS_DIR / "nova.log"

            LoggerManager.setup_logging(
                log_level_name=log_level,
                log_file=log_path,
                console_output=self.config_manager.get("logging.console_output", True),
                file_output=self.config_manager.get("logging.file_output", True),
            )

            logger.info("Initializing NOVA Application (Day 2 AI Architecture)...")

            # Step 3: Service Registry Instantiation
            self.service_manager = ServiceManager()

            # Step 4: Register Core Services
            fs_service = FileSystemService(self.config_manager)
            mem_service = MemoryService(self.config_manager)
            ollama_service = OllamaService(self.config_manager)

            # Step 5: Register AI Engine Service
            self.ai_engine = AIEngineService(self.config_manager, memory_service=mem_service)

            self.service_manager.register(fs_service)
            self.service_manager.register(mem_service)
            self.service_manager.register(ollama_service)
            self.service_manager.register(self.ai_engine)

            # Step 6: Initialize All Registered Services
            init_results = self.service_manager.initialize_all()

            self.is_initialized = True
            logger.info("Bootstrap sequence finished successfully.")

            # Step 7: Display Startup Banner
            StartupBanner.display(self.config_manager, self.service_manager)

            return True

        except NovaException as e:
            logger.critical(f"NOVA System Error during bootstrap: {e}")
            print(f"\n\033[91m[CRITICAL BOOTSTRAP ERROR] {e}\033[0m", file=sys.stderr)
            return False
        except Exception as e:
            logger.critical(f"Unexpected fatal error during bootstrap: {e}", exc_info=True)
            print(f"\n\033[91m[FATAL UNHANDLED ERROR] {e}\033[0m", file=sys.stderr)
            return False

    def shutdown(self) -> None:
        """Gracefully shuts down NOVA and all registered services."""
        if self.service_manager:
            logger.info("Shutting down NOVA application...")
            self.service_manager.shutdown_all()
        logger.info("NOVA Application stopped.")
