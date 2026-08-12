"""
NOVA AI Engine Service Core with Performance Optimizations & Streaming Support
"""
import logging
import time
from typing import Any, Dict, Generator, List, Optional

from nova.core.base_service import BaseService, ServiceStatus
from nova.core.config import ConfigManager
from nova.services.memory_service import MemoryService
from nova.ai.ollama_client import OllamaClient
from nova.ai.system_prompt import SystemPromptManager
from nova.ai.prompt_builder import PromptBuilder
from nova.ai.session_manager import SessionManager
from nova.ai.response_processor import ResponseProcessor, ProcessedResponse
from nova.ai.ai_status_manager import AIStatusManager
from nova.utils.constants import AIEngineError, OllamaClientError, PromptBuilderError

logger = logging.getLogger("NOVA.AIEngineService")


class AIEngineService(BaseService):
    """
    Central AI Gateway and Orchestrator for NOVA.
    Encapsulates all AI communication, session handling, prompt construction,
    response processing, latency optimization, and status tracking.
    """

    def __init__(self, config_manager: ConfigManager, memory_service: Optional[MemoryService] = None):
        super().__init__(name="AIEngineService", description="Central AI Gateway & Local Ollama Orchestration Engine")
        self.config_manager = config_manager
        self.memory_service = memory_service

        # Read configuration parameters dynamically
        host = config_manager.get("ollama.host", "localhost")
        port = config_manager.get("ollama.port", 11434)
        timeout = config_manager.get("ollama.timeout_seconds", 300)
        keep_alive = config_manager.get("ollama.keep_alive", "30m")
        self.target_model = config_manager.get("ollama.model", "qwen2.5:14b")
        self.options = config_manager.get("ollama.options", {
            "num_ctx": 2048,
            "num_predict": 512,
            "temperature": 0.7,
            "top_p": 0.9,
        })

        # Sub-modules
        self.client = OllamaClient(host=host, port=port, timeout=timeout, keep_alive=keep_alive)
        self.system_prompt_manager = SystemPromptManager()
        self.prompt_builder = PromptBuilder(self.system_prompt_manager)
        self.session_manager = SessionManager()
        self.status_manager = AIStatusManager(target_model=self.target_model)

    def initialize(self) -> bool:
        # Re-read options in initialize after config file load
        self.target_model = self.config_manager.get("ollama.model", "qwen2.5:14b")
        self.options = self.config_manager.get("ollama.options", self.options)
        self.client.timeout = self.config_manager.get("ollama.timeout_seconds", 300)
        self.client.keep_alive = self.config_manager.get("ollama.keep_alive", "30m")

        self._set_status(ServiceStatus.INITIALIZING, f"Connecting AI Engine to Ollama (Target model: {self.target_model})")
        logger.info(f"Initializing AI Engine Service (Target model: {self.target_model})...")

        # 1. Inject memory profile instructions into System Prompt if memory service available
        self._sync_memory_instructions()

        # 2. Check Ollama server connectivity & model availability
        connected, version = self.client.check_connection()
        model_available = self.client.is_model_available(self.target_model) if connected else False

        self.status_manager.update_connection(is_connected=connected, model_loaded=model_available)

        details = {
            "target_model": self.target_model,
            "connected": connected,
            "ollama_version": version,
            "model_available": model_available,
            "active_session": self.session_manager.active_session_name,
            "inference_options": self.options,
        }

        if connected and model_available:
            msg = f"Ready ({self.target_model} online via Ollama v{version})"
            logger.info(f"AI Engine Service ready. Model '{self.target_model}' verified.")
            self._set_status(ServiceStatus.HEALTHY, msg, details=details)
            return True
        elif connected:
            msg = f"Ollama online, but model '{self.target_model}' is not pulled"
            logger.warning(msg)
            details["remedy"] = f"Run `ollama pull {self.target_model}`"
            self._set_status(ServiceStatus.DEGRADED, msg, details=details)
            return False
        else:
            msg = f"Ollama daemon unreachable at {self.client.base_url}"
            logger.warning(msg)
            details["remedy"] = "Start Ollama server with `ollama serve`"
            self._set_status(ServiceStatus.FAILED, msg, details=details)
            return False

    def chat(self, user_input: str, session_id: Optional[str] = None) -> ProcessedResponse:
        """
        Non-streaming multi-turn conversation entry point.
        """
        if not user_input or not user_input.strip():
            logger.warning("Empty user prompt received.")
            return ResponseProcessor.process("[NOVA AI Engine Warning]: Prompt cannot be empty.")

        if session_id and session_id != self.session_manager.active_session_id:
            self.session_manager.switch_session(session_id)

        conv = self.session_manager.get_active_conversation()
        memory_ctx = self._get_memory_context()

        try:
            messages = self.prompt_builder.build_chat_messages(
                user_input=user_input,
                history=conv.get_history(),
                memory_context=memory_ctx,
            )

            conv.add_user_message(user_input)
            start_time = time.time()

            raw_response = self.client.chat(
                model=self.target_model,
                messages=messages,
                options=self.options,
            )

            latency_ms = (time.time() - start_time) * 1000.0

            message_obj = raw_response.get("message", {})
            raw_content = message_obj.get("content", "")

            processed = ResponseProcessor.process(raw_content=raw_content, raw_metadata=raw_response)

            conv.add_assistant_message(processed.cleaned_content, metadata={"latency_ms": latency_ms})
            self.session_manager.save_session(self.session_manager.active_session_id)

            self.status_manager.record_request_success(
                latency_ms=latency_ms,
                active_session_name=self.session_manager.active_session_name,
            )

            return processed

        except OllamaClientError as e:
            logger.error(f"Ollama client error during chat: {e}")
            self.status_manager.record_request_error()
            fallback_msg = f"[NOVA AI Engine Error]: Could not communicate with local Ollama server.\nDetail: {e}"
            return ResponseProcessor.process(fallback_msg)
        except Exception as e:
            logger.error(f"Unexpected AI Engine error: {e}", exc_info=True)
            self.status_manager.record_request_error()
            fallback_msg = f"[NOVA AI Engine Fatal Error]: An unexpected error occurred: {e}"
            return ResponseProcessor.process(fallback_msg)

    def chat_stream(self, user_input: str, session_id: Optional[str] = None) -> Generator[str, None, ProcessedResponse]:
        """
        Streaming multi-turn conversation entry point.
        Yields individual token strings in real-time as received from LLM.
        Final return value is ProcessedResponse object.
        """
        if not user_input or not user_input.strip():
            yield "[NOVA AI Engine Warning]: Prompt cannot be empty."
            return ResponseProcessor.process("")

        if session_id and session_id != self.session_manager.active_session_id:
            self.session_manager.switch_session(session_id)

        conv = self.session_manager.get_active_conversation()
        memory_ctx = self._get_memory_context()

        messages = self.prompt_builder.build_chat_messages(
            user_input=user_input,
            history=conv.get_history(),
            memory_context=memory_ctx,
        )

        conv.add_user_message(user_input)
        start_time = time.time()
        chunks: List[str] = []

        try:
            for token in self.client.chat_stream(model=self.target_model, messages=messages, options=self.options):
                chunks.append(token)
                yield token

            latency_ms = (time.time() - start_time) * 1000.0
            full_raw = "".join(chunks)
            processed = ResponseProcessor.process(raw_content=full_raw)

            conv.add_assistant_message(processed.cleaned_content, metadata={"latency_ms": latency_ms})
            self.session_manager.save_session(self.session_manager.active_session_id)

            self.status_manager.record_request_success(
                latency_ms=latency_ms,
                active_session_name=self.session_manager.active_session_name,
            )

            return processed

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            self.status_manager.record_request_error()
            err_msg = f"\n[NOVA AI Engine Error]: {e}"
            yield err_msg
            return ResponseProcessor.process(err_msg)

    def generate(self, prompt: str) -> ProcessedResponse:
        """
        Single-turn completion entry point without session state tracking.
        """
        if not prompt or not prompt.strip():
            return ResponseProcessor.process("[NOVA AI Engine Warning]: Prompt cannot be empty.")

        memory_ctx = self._get_memory_context()

        try:
            sys_prompt, user_prompt = self.prompt_builder.build_single_prompt(
                user_input=prompt,
                memory_context=memory_ctx,
            )

            start_time = time.time()
            raw_response = self.client.generate(
                model=self.target_model,
                prompt=user_prompt,
                system=sys_prompt,
                options=self.options,
            )
            latency_ms = (time.time() - start_time) * 1000.0

            raw_content = raw_response.get("response", "")
            processed = ResponseProcessor.process(raw_content=raw_content, raw_metadata=raw_response)

            self.status_manager.record_request_success(
                latency_ms=latency_ms,
                active_session_name=self.session_manager.active_session_name,
            )
            return processed

        except Exception as e:
            logger.error(f"Generate error: {e}")
            self.status_manager.record_request_error()
            return ResponseProcessor.process(f"[NOVA AI Engine Error]: Single completion failed: {e}")

    def create_session(self, name: str) -> str:
        return self.session_manager.create_session(name)

    def switch_session(self, session_id: str) -> bool:
        return self.session_manager.switch_session(session_id)

    def list_sessions(self) -> List[Dict[str, Any]]:
        return self.session_manager.list_sessions()

    def get_ai_status(self) -> Dict[str, Any]:
        return self.status_manager.get_status_report()

    def shutdown(self) -> None:
        self.session_manager.save_session(self.session_manager.active_session_id)
        self._set_status(ServiceStatus.SHUTDOWN, "AIEngineService stopped")

    def _sync_memory_instructions(self) -> None:
        if not self.memory_service:
            return

        profile = self.memory_service.get_memory("user_profile.json")
        if profile and "custom_instructions" in profile:
            instructions = profile.get("custom_instructions", [])
            self.system_prompt_manager.set_custom_instructions(instructions)

    def _get_memory_context(self) -> Dict[str, Any]:
        ctx: Dict[str, Any] = {}
        if not self.memory_service:
            return ctx

        profile = self.memory_service.get_memory("user_profile.json")
        if profile:
            ctx["user_name"] = profile.get("user_name", "User")

        long_term = self.memory_service.get_memory("long_term.json")
        if long_term:
            ctx["preferences"] = long_term.get("preferences", {})
            ctx["facts"] = long_term.get("facts", {})

        return ctx
