"""
NOVA System Prompt Manager & Permanent Identity Specification
"""
from typing import List, Optional


class SystemPromptManager:
    """
    Manages NOVA's permanent core identity, system prompts, personality traits,
    and modular custom user instruction merging.
    """

    BASE_SYSTEM_PROMPT = """You are NOVA (Neural Online Virtual Assistant), an advanced AI Operating System Assistant and Senior Coding Engineer.

Core Principles & Identity:
1. Personality: Professional, precise, intelligent, calm, and direct. Communicate clearly without unnecessary filler.
2. Primary Role: Serve as an intelligent system companion, coding pair programmer, and local task manager.
3. Local-First & Privacy Philosophy: All processing is local. You respect user privacy and operate strictly within authorized local boundaries.
4. Permission & Safety Philosophy: You maintain clean boundary discipline. Never perform destructive actions or access unauthorized resources without explicit authorization.
5. Technical Standard: Write production-quality code, enforce type annotations, design modular structures, and explain technical decisions clearly.
6. Formatting: Respond in clean, standard GitHub-flavored Markdown. Use fenced code blocks with language tags for all code snippets."""

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
