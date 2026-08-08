"""
NOVA Service Registry Manager
"""
from typing import Dict, List, Optional, Type, TypeVar
import logging

from nova.core.base_service import BaseService, ServiceStatus
from nova.utils.constants import ServiceError

T = TypeVar("T", bound=BaseService)
logger = logging.getLogger("NOVA.ServiceManager")


class ServiceManager:
    """
    Central service registry allowing registration, lookup, initialization,
    and lifecycle management of core system services.
    """

    def __init__(self):
        self._services: Dict[str, BaseService] = {}

    def register(self, service: BaseService) -> BaseService:
        """
        Registers a service instance in the manager.
        """
        if service.name in self._services:
            logger.warning(f"Overwriting previously registered service: {service.name}")
        self._services[service.name] = service
        logger.debug(f"Registered service '{service.name}' ({service.description})")
        return service

    def get(self, name: str) -> Optional[BaseService]:
        """
        Retrieves a registered service by name.
        """
        return self._services.get(name)

    def get_typed(self, service_type: Type[T]) -> Optional[T]:
        """
        Retrieves a service by its class type.
        """
        for service in self._services.values():
            if isinstance(service, service_type):
                return service
        return None

    def initialize_all(self) -> Dict[str, bool]:
        """
        Initializes all registered services in order of registration.
        Returns a mapping of service name to initialization success status.
        """
        results: Dict[str, bool] = {}
        logger.info(f"Initializing {len(self._services)} registered service(s)...")

        for name, service in self._services.items():
            logger.info(f"Initializing service: [{name}]...")
            try:
                success = service.initialize()
                results[name] = success
                if success:
                    logger.info(f"Service [{name}] initialized successfully.")
                else:
                    logger.warning(f"Service [{name}] initialized with warnings/degraded status.")
            except Exception as e:
                results[name] = False
                logger.error(f"Failed to initialize service [{name}]: {e}", exc_info=True)

        return results

    def shutdown_all(self) -> None:
        """
        Gracefully shuts down all registered services in reverse registration order.
        """
        logger.info("Shutting down registered services...")
        for name in reversed(list(self._services.keys())):
            service = self._services[name]
            try:
                service.shutdown()
                logger.info(f"Service [{name}] shut down gracefully.")
            except Exception as e:
                logger.error(f"Error shutting down service [{name}]: {e}")

    def get_all_statuses(self) -> Dict[str, Dict]:
        """
        Returns status reports for all registered services.
        """
        return {name: service.get_status() for name, service in self._services.items()}

    def get_system_health(self) -> Dict[str, int]:
        """
        Calculates counts of healthy, degraded, and failed services.
        """
        counts = {"total": len(self._services), "healthy": 0, "degraded": 0, "failed": 0, "uninitialized": 0}

        for service in self._services.values():
            st = service.status
            if st == ServiceStatus.HEALTHY:
                counts["healthy"] += 1
            elif st == ServiceStatus.DEGRADED:
                counts["degraded"] += 1
            elif st in (ServiceStatus.FAILED, ServiceStatus.SHUTDOWN):
                counts["failed"] += 1
            else:
                counts["uninitialized"] += 1

        return counts
