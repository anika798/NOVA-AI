"""
NOVA Logging Manager
"""
import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
from typing import Optional


class ColoredConsoleFormatter(logging.Formatter):
    """Custom formatter adding ANSI color accents to terminal log output."""

    COLOR_CODES = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLOR_CODES.get(record.levelno, self.RESET)
        log_fmt = f"\033[90m%(asctime)s\033[0m [{color}%(levelname)-8s{self.RESET}] \033[37m%(name)s:\033[0m %(message)s"
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


class LoggerManager:
    """
    Centralized logging initialization system for NOVA.
    Supports formatted console stream output and rotating file output.
    """

    _initialized = False

    @classmethod
    def setup_logging(
        cls,
        log_level_name: str = "INFO",
        log_file: Optional[Path] = None,
        console_output: bool = True,
        file_output: bool = True,
        max_bytes: int = 10485760,
        backup_count: int = 5,
    ) -> logging.Logger:
        """
        Initializes root logger and handlers.
        """
        root_logger = logging.getLogger("NOVA")
        log_level = getattr(logging, log_level_name.upper(), logging.INFO)
        root_logger.setLevel(log_level)

        # Clear existing handlers to prevent duplicate output on re-init
        if root_logger.hasHandlers():
            root_logger.handlers.clear()

        # Console Handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(ColoredConsoleFormatter())
            root_logger.addHandler(console_handler)

        # File Handler
        if file_output and log_file:
            try:
                log_file.parent.mkdir(parents=True, exist_ok=True)
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding="utf-8",
                )
                file_handler.setLevel(log_level)
                file_fmt = logging.Formatter(
                    "%(asctime)s [%(levelname)s] [%(name)s:%(filename)s:%(lineno)d] - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
                file_handler.setFormatter(file_fmt)
                root_logger.addHandler(file_handler)
            except Exception as e:
                # Fallback print if file logging target cannot be opened
                print(f"[NOVA LOGGER WARN] Unable to open log file {log_file}: {e}")

        cls._initialized = True
        return root_logger

    @classmethod
    def get_logger(cls, name: str = "NOVA") -> logging.Logger:
        """Returns named logger instance."""
        return logging.getLogger(f"NOVA.{name}" if name != "NOVA" else "NOVA")
