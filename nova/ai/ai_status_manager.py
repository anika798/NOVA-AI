"""
NOVA AI Status & Performance Telemetry Manager
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class AIStatusManager:
    """
    Tracks state, performance metrics, response latency, and connectivity status for NOVA AI Engine.
    """

    def __init__(self, target_model: str = "qwen2.5:14b"):
        self.target_model: str = target_model
        self.is_connected: bool = False
        self.model_loaded: bool = False
        self.active_session_id: str = "default"
        self.active_session_name: str = "Default Session"
        
        self.total_requests: int = 0
        self.total_errors: int = 0
        self.last_latency_ms: float = 0.0
        self.avg_latency_ms: float = 0.0
        self.last_request_time: Optional[str] = None
        
        self._total_latency_accum: float = 0.0

    def update_connection(self, is_connected: bool, model_loaded: bool) -> None:
        """Updates connectivity and model verification state."""
        self.is_connected = is_connected
        self.model_loaded = model_loaded

    def record_request_success(self, latency_ms: float, active_session_name: str = "Default Session") -> None:
        """Records telemetry metrics for a successful LLM request."""
        self.total_requests += 1
        self.last_latency_ms = round(latency_ms, 2)
        self._total_latency_accum += latency_ms
        self.avg_latency_ms = round(self._total_latency_accum / self.total_requests, 2)
        self.last_request_time = datetime.now(timezone.utc).isoformat()
        self.active_session_name = active_session_name

    def record_request_error(self) -> None:
        """Increments error counter for telemetry."""
        self.total_errors += 1
        self.last_request_time = datetime.now(timezone.utc).isoformat()

    def get_status_report(self) -> Dict[str, Any]:
        """Returns snapshot dictionary of current AI Engine status metrics."""
        return {
            "model": self.target_model,
            "connected": self.is_connected,
            "model_loaded": self.model_loaded,
            "active_session": self.active_session_name,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "last_latency_ms": self.last_latency_ms,
            "avg_latency_ms": self.avg_latency_ms,
            "last_request_time": self.last_request_time,
        }
