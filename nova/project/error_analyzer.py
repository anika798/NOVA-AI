"""
NOVA Error Analysis & Classification Subsystem
"""
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("NOVA.ErrorAnalyzer")


class ErrorAnalyzer:
    """
    Parses and classifies process stderr/traceback outputs into structured error categories,
    identifying root causes, missing dependencies, and suggested fix strategies.
    """

    ERROR_PATTERNS = [
        (r"ModuleNotFoundError:\s*No module named ['\"]([^'\"]+)['\"]", "ModuleNotFoundError"),
        (r"ImportError:\s*(.+)", "ImportError"),
        (r"SyntaxError:\s*(.+)", "SyntaxError"),
        (r"IndentationError:\s*(.+)", "SyntaxError"),
        (r"FileNotFoundError:\s*(.+)", "FileNotFoundError"),
        (r"PermissionError:\s*(.+)", "PermissionError"),
        (r"TypeError:\s*(.+)", "TypeError"),
        (r"ValueError:\s*(.+)", "ValueError"),
        (r"AttributeError:\s*(.+)", "AttributeError"),
        (r"KeyError:\s*(.+)", "KeyError"),
        (r"IndexError:\s*(.+)", "IndexError"),
        (r"NameError:\s*(.+)", "NameError"),
        (r"ZeroDivisionError:\s*(.+)", "RuntimeError"),
        (r"ConnectionRefusedError|\b(eaddrinuse|port in use)\b", "Port/NetworkError"),
    ]

    def analyze(self, stderr: str, stdout: Optional[str] = None, exit_code: int = -1) -> Dict[str, Any]:
        """
        Analyzes stderr/stdout text and returns structured error diagnosis.
        """
        combined_text = (stderr or "") + "\n" + (stdout or "")
        if not combined_text.strip() or exit_code == 0:
            # Check if exit_code == 0 and no explicit error pattern was matched in combined_text
            has_explicit_error = any(re.search(pattern, combined_text, re.IGNORECASE) for pattern, _ in self.ERROR_PATTERNS)
            if exit_code == 0 and not has_explicit_error:
                return {
                    "error_type": "None",
                    "raw_message": "Clean exit.",
                    "likely_cause": "No error.",
                    "suggested_action": "None required.",
                    "target_package": None,
                    "is_recoverable": False,
                }
            if not combined_text.strip():
                return {
                    "error_type": "UnknownError" if exit_code != 0 else "None",
                    "raw_message": "Process returned non-zero exit code without stderr output." if exit_code != 0 else "Clean exit.",
                    "likely_cause": "Unspecified process exit failure." if exit_code != 0 else "No error.",
                    "suggested_action": "Inspect stdout or application logs.",
                    "target_package": None,
                    "is_recoverable": exit_code != 0,
                }


        # Scan for known error patterns
        matched_type = "UnknownError"
        raw_msg = ""
        target_package = None

        for pattern, err_type in self.ERROR_PATTERNS:
            match = re.search(pattern, combined_text, re.IGNORECASE)
            if match:
                matched_type = err_type
                raw_msg = match.group(0)

                if err_type == "ModuleNotFoundError":
                    # Extract module name
                    target_package = match.group(1).split(".")[0].strip()
                elif err_type == "ImportError":
                    # Check if 'cannot import name' or module mentioned
                    mod_match = re.search(r"cannot import name ['\"]([^'\"]+)['\"]", raw_msg)
                    if mod_match:
                        target_package = mod_match.group(1)
                break

        # If no specific pattern matched, extract last line of stderr
        if matched_type == "UnknownError":
            lines = [l.strip() for l in combined_text.splitlines() if l.strip()]
            raw_msg = lines[-1] if lines else "Unknown runtime exception"

        likely_cause, suggested_action, is_recoverable = self._get_cause_and_action(matched_type, raw_msg, target_package)

        return {
            "error_type": matched_type,
            "raw_message": raw_msg,
            "likely_cause": likely_cause,
            "suggested_action": suggested_action,
            "target_package": target_package,
            "is_recoverable": is_recoverable,
        }

    def _get_cause_and_action(self, err_type: str, raw_msg: str, target_pkg: Optional[str]) -> tuple[str, str, bool]:
        if err_type == "ModuleNotFoundError":
            cause = f"Missing Python dependency package '{target_pkg or 'unknown'}' in execution environment."
            action = f"Install missing package '{target_pkg}' using pip into active project environment."
            return cause, action, True

        elif err_type == "ImportError":
            cause = f"Circular import or missing symbol/module: {raw_msg}"
            action = "Check import statements, circular references, and package versions."
            return cause, action, True

        elif err_type == "SyntaxError":
            cause = f"Python syntax error in script: {raw_msg}"
            action = "Correct syntax error, missing brackets/quotes, or indentation in source code."
            return cause, action, True

        elif err_type == "FileNotFoundError":
            cause = f"Missing file or directory resource: {raw_msg}"
            action = "Create missing file/directory or fix file path reference."
            return cause, action, True

        elif err_type == "PermissionError":
            cause = f"Permission denied accessing resource: {raw_msg}"
            action = "Check file/directory permissions or path safety rules."
            return cause, action, False

        elif err_type in ("TypeError", "ValueError", "AttributeError", "NameError", "KeyError", "IndexError"):
            cause = f"Python code runtime logic exception: {raw_msg}"
            action = "Modify source code logic to fix variable types, undefined attributes, or missing keys."
            return cause, action, True

        elif err_type == "Port/NetworkError":
            cause = f"Network or port conflict: {raw_msg}"
            action = "Free up occupied network port or check host connection configuration."
            return cause, action, True

        else:
            cause = f"Unclassified execution failure: {raw_msg}"
            action = "Analyze stack trace and apply code fix or configuration update."
            return cause, action, True
