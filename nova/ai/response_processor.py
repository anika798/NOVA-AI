"""
NOVA LLM Response Processor
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProcessedResponse:
    """Structured result object containing sanitized content and response metadata."""

    raw_content: str
    cleaned_content: str
    word_count: int
    char_count: int
    has_code_blocks: bool
    code_blocks: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResponseProcessor:
    """
    Cleans, normalizes, and extracts structured metadata from raw LLM responses.
    """

    CODE_BLOCK_PATTERN = re.compile(r"```(?P<lang>[a-zA-Z0-9_-]*)\n(?P<code>.*?)```", re.DOTALL)

    @classmethod
    def process(cls, raw_content: str, raw_metadata: Optional[Dict[str, Any]] = None) -> ProcessedResponse:
        """
        Processes raw LLM response text, normalizing whitespace and extracting code blocks.
        """
        if not raw_content:
            return ProcessedResponse(
                raw_content="",
                cleaned_content="",
                word_count=0,
                char_count=0,
                has_code_blocks=False,
                code_blocks=[],
                metadata=raw_metadata or {},
            )

        # 1. Strip leading/trailing space & normalize CRLF line endings
        cleaned = raw_content.replace("\r\n", "\n").strip()

        # 2. Extract code blocks
        code_blocks: List[Dict[str, str]] = []
        for match in cls.CODE_BLOCK_PATTERN.finditer(cleaned):
            lang = match.group("lang").strip() or "text"
            code = match.group("code").strip()
            code_blocks.append({"language": lang, "code": code})

        # 3. Calculate word and character telemetry
        words = len(cleaned.split())
        chars = len(cleaned)

        return ProcessedResponse(
            raw_content=raw_content,
            cleaned_content=cleaned,
            word_count=words,
            char_count=chars,
            has_code_blocks=len(code_blocks) > 0,
            code_blocks=code_blocks,
            metadata=raw_metadata or {},
        )
