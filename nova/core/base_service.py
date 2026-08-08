"""
NOVA Service Base Contract
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional


class ServiceStatus(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZING = "INITIALIZING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    SHUTDOWN = "SHUTDOWN"


class BaseService(ABC):
    """
    Abstract Base Class establishing the contract for all NOVA system services.
    Every service must implement lifecycle methods and health checks.
    """

    def __init__(self, name: str, description: str = ""):
        self.name: str = name
        self.description: str = description
        self._status: ServiceStatus = ServiceStatus.UNINITIALIZED
        self._status_message: str = "Not initialized"
        self._details: Dict[str, Any] = {}

    @property
    def status(self) -> ServiceStatus:
        """Returns current service health state."""
        return self._status

    @property
    def is_healthy(self) -> bool:
        """Returns True if service is in HEALTHY or DEGRADED state."""
        return self._status in (ServiceStatus.HEALTHY, ServiceStatus.DEGRADED)

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initializes the service and resources.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        Gracefully releases resources and shuts down service.
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """
        Returns structured telemetry and health report for the service.
        """
        return {
            "name": self.name,
            "description": self.description,
            "status": self._status.value,
            "message": self._status_message,
            "healthy": self.is_healthy,
            "details": self._details,
        }

    def _set_status(self, status: ServiceStatus, message: str = "", details: Optional[Dict[str, Any]] = None) -> None:
        """Internal helper to set status state and telemetry details."""
        self._status = status
        self._status_message = message
        if details is not None:
            self._details = details
