"""Centralized logging configuration for saitest.

This module provides consistent logging configuration across all saitest components
with support for different log levels, formatters, and progress indicators.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Foreground colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright foreground colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels."""
    
    # Map log levels to colors
    LEVEL_COLORS = {
        logging.DEBUG: Colors.BRIGHT_BLACK,
        logging.INFO: Colors.BRIGHT_BLUE,
        logging.WARNING: Colors.BRIGHT_YELLOW,
        logging.ERROR: Colors.BRIGHT_RED,
        logging.CRITICAL: Colors.BOLD + Colors.BRIGHT_RED,
    }
    
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None, use_colors: bool = True):
        """Initialize colored formatter.
        
        Args:
            fmt: Log format string
            datefmt: Date format string
            use_colors: Whether to use colors (disable for file logging)
        """
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors.
        
        Args:
            record: Log record to format
        
        Returns:
            Formatted log string with colors
        """
        if self.use_colors and sys.stdout.isatty():
            # Add color to level name
            levelname = record.levelname
            color = self.LEVEL_COLORS.get(record.levelno, '')
            record.levelname = f"{color}{levelname}{Colors.RESET}"
            
            # Format the message
            formatted = super().format(record)
            
            # Reset levelname for other formatters
            record.levelname = levelname
            
            return formatted
        else:
            return super().format(record)


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    verbose: bool = False,
    quiet: bool = False
) -> None:
    """Configure logging for saitest.
    
    Sets up console and optional file logging with appropriate formatters
    and log levels.
    
    Args:
        level: Base logging level (default: INFO)
        log_file: Optional path to log file for persistent logging
        verbose: Enable verbose (DEBUG) logging
        quiet: Suppress all but ERROR and CRITICAL messages
    """
    # Determine effective log level
    if quiet:
        effective_level = logging.ERROR
    elif verbose:
        effective_level = logging.DEBUG
    else:
        effective_level = level
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(effective_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(effective_level)
    
    # Use colored formatter for console
    console_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    console_formatter = ColoredFormatter(
        fmt=console_format,
        datefmt='%Y-%m-%d %H:%M:%S',
        use_colors=True
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if log file specified
    if log_file:
        try:
            # Ensure log directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file
            
            # Use plain formatter for file (no colors)
            file_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            file_formatter = logging.Formatter(
                fmt=file_format,
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            
            root_logger.info(f"Logging to file: {log_file}")
            
        except Exception as e:
            root_logger.warning(f"Failed to setup file logging: {e}")
    
    # Set specific log levels for noisy libraries
    logging.getLogger('docker').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('anthropic').setLevel(logging.WARNING)
    
    # Log initial configuration
    root_logger.debug(
        f"Logging configured: level={logging.getLevelName(effective_level)}, "
        f"file={log_file if log_file else 'none'}"
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the specified name.
    
    This is a convenience function that ensures consistent logger naming.
    
    Args:
        name: Logger name (typically __name__ of the module)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class ProgressIndicator:
    """Progress indicator for long-running operations.
    
    Provides visual feedback for operations that take time, such as
    container operations, LLM calls, and file processing.
    """
    
    def __init__(self, description: str, logger: Optional[logging.Logger] = None):
        """Initialize progress indicator.
        
        Args:
            description: Description of the operation
            logger: Optional logger for progress messages
        """
        self.description = description
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = None
        self.is_active = False
    
    def start(self) -> None:
        """Start the progress indicator."""
        self.start_time = datetime.now()
        self.is_active = True
        self.logger.info(f"⏳ {self.description}...")
    
    def update(self, message: str) -> None:
        """Update progress with a message.
        
        Args:
            message: Progress update message
        """
        if self.is_active:
            self.logger.info(f"   {message}")
    
    def complete(self, success: bool = True, message: Optional[str] = None) -> None:
        """Complete the progress indicator.
        
        Args:
            success: Whether the operation succeeded
            message: Optional completion message
        """
        if not self.is_active:
            return
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        if success:
            status = f"{Colors.GREEN}✓{Colors.RESET}"
            level = logging.INFO
        else:
            status = f"{Colors.RED}✗{Colors.RESET}"
            level = logging.ERROR
        
        completion_msg = f"{status} {self.description}"
        if message:
            completion_msg += f": {message}"
        completion_msg += f" ({elapsed:.1f}s)"
        
        self.logger.log(level, completion_msg)
        self.is_active = False
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is None:
            self.complete(success=True)
        else:
            self.complete(success=False, message=str(exc_val))
        return False  # Don't suppress exceptions


def log_exception(logger: logging.Logger, message: str, exc: Exception, include_traceback: bool = True) -> None:
    """Log an exception with consistent formatting.
    
    Args:
        logger: Logger instance
        message: Context message describing what failed
        exc: Exception that was raised
        include_traceback: Whether to include full traceback
    """
    error_msg = f"{message}: {type(exc).__name__}: {str(exc)}"
    
    if include_traceback:
        logger.error(error_msg, exc_info=True)
    else:
        logger.error(error_msg)


def log_operation_start(logger: logging.Logger, operation: str, **kwargs) -> None:
    """Log the start of an operation with parameters.
    
    Args:
        logger: Logger instance
        operation: Name of the operation
        **kwargs: Operation parameters to log
    """
    params = ', '.join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"Starting {operation}" + (f" with {params}" if params else ""))


def log_operation_complete(
    logger: logging.Logger,
    operation: str,
    success: bool,
    duration: Optional[float] = None,
    **kwargs
) -> None:
    """Log the completion of an operation.
    
    Args:
        logger: Logger instance
        operation: Name of the operation
        success: Whether the operation succeeded
        duration: Optional duration in seconds
        **kwargs: Additional result information to log
    """
    status = "completed successfully" if success else "failed"
    msg = f"{operation} {status}"
    
    if duration is not None:
        msg += f" in {duration:.2f}s"
    
    if kwargs:
        details = ', '.join(f"{k}={v}" for k, v in kwargs.items())
        msg += f" ({details})"
    
    level = logging.INFO if success else logging.ERROR
    logger.log(level, msg)
