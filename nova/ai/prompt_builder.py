"""
NOVA Prompt Builder
"""
from typing import Any, Dict, List, Optional, Tuple
import logging

from nova.ai.system_prompt import SystemPromptManager
from nova.utils.constants import PromptBuilderError

logger = logging.getLogger("NOVA.PromptBuilder")


class PromptBuilder:
    """
    Constructs unified LLM prompt structures by composing System Prompts,
    Memory Context, Session History, and User Inputs into Ollama payload specs.
    """

    def __init__(self, system_prompt_manager: Optional[SystemPromptManager] = None):
        self.system_prompt_manager = system_prompt_manager or SystemPromptManager()

    def build_chat_messages(
        self,
        user_input: str,
        history: List[Dict[str, str]],
        memory_context: Optional[Dict[str, Any]] = None,
        additional_instructions: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        """
        Builds structured list of chat messages for Ollama /api/chat.

        Format:
        [
            {"role": "system", "content": ...},
            {"role": "user" / "assistant", "content": ...},
            ...
            {"role": "user", "content": user_input}
        ]
        """
        if not user_input or not user_input.strip():
            raise PromptBuilderError("User prompt cannot be empty.")

        # Update custom instructions if provided
        if additional_instructions:
            self.system_prompt_manager.set_custom_instructions(additional_instructions)

        # Build Memory Context Summary
        context_str = self._format_memory_context(memory_context) if memory_context else None

        # Build System Message
        system_content = self.system_prompt_manager.build_system_prompt(additional_context=context_str)

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]

        # Append Conversation History
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant", "system") and content:
                messages.append({"role": role, "content": content})

        # Append current user prompt
        messages.append({"role": "user", "content": user_input.strip()})

        return messages

    def build_single_prompt(
        self,
        user_input: str,
        memory_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """
        Builds single completion prompt and system prompt for Ollama /api/generate.
        Returns tuple of (system_prompt, user_prompt).
        """
        if not user_input or not user_input.strip():
            raise PromptBuilderError("User prompt cannot be empty.")

        context_str = self._format_memory_context(memory_context) if memory_context else None
        system_content = self.system_prompt_manager.build_system_prompt(additional_context=context_str)

        return system_content, user_input.strip()

    def _format_memory_context(self, memory_context: Dict[str, Any]) -> str:
        """Formats memory JSON snippets into clean system prompt context section."""
        lines: List[str] = []

        if "user_name" in memory_context:
            lines.append(f"User: {memory_context['user_name']}")

        if "preferences" in memory_context and memory_context["preferences"]:
            prefs = memory_context["preferences"]
            lines.append(f"Known User Preferences: {prefs}")

        if "facts" in memory_context and memory_context["facts"]:
            facts = memory_context["facts"]
            lines.append(f"Retained Knowledge Facts: {facts}")

        return "\n".join(lines)
