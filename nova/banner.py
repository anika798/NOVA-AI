"""
NOVA Startup Banner Renderer
"""
import sys
from typing import Dict, Any, Optional

from nova.core.config import ConfigManager
from nova.core.service_manager import ServiceManager


class StartupBanner:
    """
    Renders formatted visual startup banner for NOVA.
    """

    # ANSI Formatting
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @classmethod
    def render(cls, config_manager: ConfigManager, service_manager: ServiceManager) -> str:
        """
        Builds and returns formatted terminal banner string.
        """
        app_name = config_manager.get("app.name", "NOVA")
        app_version = config_manager.get("app.version", "1.0.0-day2")
        app_mode = config_manager.get("app.mode", "Development")
        configured_model = config_manager.get("ollama.model", "qwen2.5:14b")

        # Gather Service Telemetry
        mem_service = service_manager.get("MemoryService")
        ollama_service = service_manager.get("OllamaService")
        ai_engine_service = service_manager.get("AIEngineService")

        # Memory Telemetry
        mem_status_str = "Unknown"
        if mem_service:
            mem_info = mem_service.get_status()
            if mem_info.get("healthy"):
                details = mem_info.get("details", {})
                count = details.get("file_count", 4)
                size_kb = details.get("total_size_kb", 0)
                mem_status_str = f"{cls.GREEN}ONLINE{cls.RESET} ({count} JSON files, {size_kb} KB)"
            else:
                mem_status_str = f"{cls.RED}INITIALIZATION FAILED{cls.RESET}"

        # Ollama Telemetry
        ollama_conn_str = f"{cls.RED}OFFLINE{cls.RESET}"
        model_status_str = f"{cls.RED}NOT FOUND{cls.RESET}"

        if ollama_service:
            ollama_info = ollama_service.get_status()
            details = ollama_info.get("details", {})
            if details.get("connected"):
                ollama_conn_str = f"{cls.GREEN}CONNECTED{cls.RESET} (v{details.get('version', 'unknown')})"
            else:
                ollama_conn_str = f"{cls.RED}DISCONNECTED{cls.RESET} ({details.get('remedy', 'Start Ollama server')})"

            if details.get("model_available"):
                model_status_str = f"{cls.GREEN}AVAILABLE & READY{cls.RESET}"
            elif details.get("connected"):
                model_status_str = f"{cls.YELLOW}MISSING{cls.RESET} (Run `ollama pull {configured_model}`)"

        # AI Engine Telemetry
        ai_brain_str = f"{cls.RED}UNINITIALIZED{cls.RESET}"
        active_sess_str = "Default Session"
        if ai_engine_service:
            ai_info = ai_engine_service.get_status()
            if ai_info.get("healthy"):
                ai_brain_str = f"{cls.GREEN}BRAIN ACTIVE{cls.RESET} ({configured_model} Communication Ready)"
            else:
                ai_brain_str = f"{cls.YELLOW}DEGRADED{cls.RESET} ({ai_info.get('message', '')})"

            details = ai_info.get("details", {})
            active_sess_str = details.get("active_session", "Default Session")

        # Overall System Health
        health = service_manager.get_system_health()
        if health["failed"] > 0:
            health_str = f"{cls.RED}DEGRADED / ATTENTION REQUIRED{cls.RESET}"
        elif health["degraded"] > 0:
            health_str = f"{cls.YELLOW}PARTIALLY HEALTHY (Ollama/Model Warning){cls.RESET}"
        else:
            health_str = f"{cls.GREEN}ALL SYSTEMS OPERATIONAL{cls.RESET}"

        lines = [
            f"{cls.CYAN}{cls.BOLD}",
            r"  _  ______  _    _        _    ___ ",
            r" | \| | __ \| |  | |      / \  |_ _|",
            r" | .` | | | | |  | |     / _ \  | | ",
            r" | |\ | |_| |\ \/ /     / ___ \ | | ",
            r" |_| \_|____/ \__/     /_/   \_\___|",
            f"{cls.RESET}",
            f"{cls.DIM}============================================================{cls.RESET}",
            f"  {cls.BOLD}Application:{cls.RESET}      {app_name} v{app_version}",
            f"  {cls.BOLD}Execution Mode:{cls.RESET}   {cls.BLUE}{app_mode}{cls.RESET}",
            f"  {cls.BOLD}Target LLM Model:{cls.RESET} {cls.CYAN}{configured_model}{cls.RESET}",
            f"  {cls.BOLD}Active Session:{cls.RESET}   {cls.YELLOW}{active_sess_str}{cls.RESET}",
            f"  {cls.BOLD}Overall Health:{cls.RESET}   {health_str}",
            f"{cls.DIM}------------------------------------------------------------{cls.RESET}",
            f"  {cls.BOLD}[AI Engine Brain]:{cls.RESET} {ai_brain_str}",
            f"  {cls.BOLD}[Memory Status]:{cls.RESET}   {mem_status_str}",
            f"  {cls.BOLD}[Ollama Server]:{cls.RESET}   {ollama_conn_str}",
            f"  {cls.BOLD}[Model Status]:{cls.RESET}    {model_status_str}",
            f"{cls.DIM}------------------------------------------------------------{cls.RESET}",
            f"  {cls.BOLD}Registered Core Services ({health['total']}):{cls.RESET}",
        ]

        # Service Table Breakdown
        statuses = service_manager.get_all_statuses()
        for name, st in statuses.items():
            healthy = st.get("healthy", False)
            status_val = st.get("status", "UNKNOWN")
            msg = st.get("message", "")

            if status_val == "HEALTHY":
                st_badge = f"{cls.GREEN}[OK]{cls.RESET}"
            elif status_val == "DEGRADED":
                st_badge = f"{cls.YELLOW}[WARN]{cls.RESET}"
            else:
                st_badge = f"{cls.RED}[FAIL]{cls.RESET}"

            lines.append(f"   • {st_badge} {name:<20} {cls.DIM}-> {msg}{cls.RESET}")

        lines.append(f"{cls.DIM}============================================================{cls.RESET}")
        return "\n".join(lines)

    @classmethod
    def display(cls, config_manager: ConfigManager, service_manager: ServiceManager) -> None:
        """Prints startup banner to standard output."""
        print(cls.render(config_manager, service_manager))
