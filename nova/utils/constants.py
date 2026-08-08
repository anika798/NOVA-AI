"""
NOVA System Constants and Exception Definitions
"""
import os
from pathlib import Path
from typing import Dict, Any

# Application Metadata
APP_NAME = "NOVA"
APP_DESCRIPTION = "Neural Online Virtual Assistant"
APP_VERSION = "1.0.0-day2"
DEFAULT_MODE = "Development"

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"
MEMORY_DIR = DATA_DIR / "memory"
SESSIONS_DIR = MEMORY_DIR / "sessions"
LOGS_DIR = DATA_DIR / "logs"

DEFAULT_CONFIG_PATH = CONFIG_DIR / "settings.json"
DEFAULT_LOG_PATH = LOGS_DIR / "nova.log"

# Default Memory Schemas
DEFAULT_MEMORY_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "short_term.json": {
        "version": "1.0",
        "description": "Transient active memory store",
        "context_buffer": [],
        "active_session": {
            "session_id": "default",
            "started_at": None,
            "interaction_count": 0
        },
        "recent_intents": []
    },
    "long_term.json": {
        "version": "1.0",
        "description": "Persistent knowledge and episode memory",
        "episodes": [],
        "facts": {},
        "preferences": {},
        "archived_topics": []
    },
    "user_profile.json": {
        "version": "1.0",
        "description": "User identity and personalization profile",
        "user_name": "Admin",
        "preferred_language": "en",
        "custom_instructions": [
            "Be concise, direct, and technically precise.",
            "Always follow clean code principles and type annotations."
        ],
        "permissions": {
            "level": "admin",
            "allowed_modules": ["core", "filesystem", "memory", "ollama", "ai_engine", "voice", "agents"]
        }
    },
    "system_state.json": {
        "version": "1.0",
        "description": "Application execution and lifecycle telemetry",
        "last_boot": None,
        "boot_count": 0,
        "active_modules": [],
        "health_status": "initialized",
        "last_known_ollama_status": "unknown"
    }
}

# Base Exception
class NovaException(Exception):
    """Base exception for all NOVA system errors."""
    pass

# Infrastructure Exceptions
class ConfigError(NovaException):
    """Raised when configuration loading or parsing fails."""
    pass

class ServiceError(NovaException):
    """Raised when service lifecycle or execution fails."""
    pass

class FileSystemError(NovaException):
    """Raised when filesystem verification or creation fails."""
    pass

class MemoryError(NovaException):
    """Raised when memory file initialization or reading fails."""
    pass

class OllamaError(NovaException):
    """Raised when communication with Ollama server fails."""
    pass

# AI Subsystem Exceptions
class AIEngineError(NovaException):
    """Base exception for AI Engine subsystem errors."""
    pass

class OllamaClientError(AIEngineError):
    """Raised when Ollama client API communication fails."""
    pass

class SessionError(AIEngineError):
    """Raised when session creation, loading, or serialization fails."""
    pass

class PromptBuilderError(AIEngineError):
    """Raised when prompt construction fails."""
    pass
