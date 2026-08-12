"""
NOVA System Prompt Manager & Permanent Identity Specification
"""
from typing import List, Optional


class SystemPromptManager:
    """
    Manages NOVA's permanent core identity, system prompts, personality traits,
    and modular custom user instruction merging.
    """

    BASE_SYSTEM_PROMPT = """You are NOVA, an advanced AI assistant and coding engineer. Be concise, precise, and direct. Respond in clean Markdown with fenced code blocks. All processing is local and privacy-first."""

    def __init__(self, default_instructions: Optional[List[str]] = None):
        self._custom_instructions: List[str] = default_instructions or []

    def set_custom_instructions(self, instructions: List[str]) -> None:
        """Sets custom user instructions (e.g. from user_profile.json memory)."""
        self._custom_instructions = instructions

    def build_system_prompt(self, additional_context: Optional[str] = None) -> str:
        """
        Assembles complete system prompt string including base identity, custom user preferences,
        and optional dynamic context hooks.
        """
        sections = [self.BASE_SYSTEM_PROMPT]

        if self._custom_instructions:
            inst_str = "\n".join(f"- {inst}" for inst in self._custom_instructions)
            sections.append(f"User Preferences & Custom Directives:\n{inst_str}")

        if additional_context:
            sections.append(f"Active System Context:\n{additional_context}")

        return "\n\n".join(sections)
