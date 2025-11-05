"""
Logging utility for the application
Provides structured logging with different levels
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from config.settings import LOG_LEVEL, LOG_FORMAT, BASE_DIR

class AppLogger:
    """Application logger with file and console handlers"""

    _loggers = {}

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get or create a logger instance"""

        if name in cls._loggers:
            return cls._loggers[name]

        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, LOG_LEVEL))

        # Prevent duplicate handlers
        if logger.handlers:
            return logger

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(LOG_FORMAT)
        console_handler.setFormatter(console_formatter)

        # File handler
        log_dir = BASE_DIR / "logs"
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(LOG_FORMAT)
        file_handler.setFormatter(file_formatter)

        # Add handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        cls._loggers[name] = logger
        return logger

# Convenience function
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return AppLogger.get_logger(name)
