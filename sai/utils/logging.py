"""Enhanced logging utilities for SAI CLI tool."""

import logging
import logging.handlers
import sys
import json
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

from ..models.config import LogLevel, SaiConfig


class LogFormat(str, Enum):
    """Log output formats."""
    STANDARD = "standard"
    JSON = "json"
    DETAILED = "detailed"
    MINIMAL = "minimal"


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability."""
    
    # ANSI color codes
    COLORS = {
        logging.DEBUG: '\033[36m',    # Cyan
        logging.INFO: '\033[32m',     # Green
        logging.WARNING: '\033[33m',  # Yellow
        logging.ERROR: '\033[31m',    # Red
        logging.CRITICAL: '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def __init__(self, fmt=None, datefmt=None, use_colors=None, *args, **kwargs):
        """Initialize colored formatter."""
        # Use a default format if none provided
        if fmt is None:
            fmt = '%(levelname)s: %(message)s'
        super().__init__(fmt, datefmt, *args, **kwargs)
        # Check if colors are supported
        if use_colors is not None:
            self.use_colors = use_colors
        else:
            self.use_colors = sys.stdout.isatty() and hasattr(sys.stdout, 'isatty')
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors if supported.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log message with colors
        """
        # Make a copy of the record to avoid modifying the original
        record_copy = logging.makeLogRecord(record.__dict__)
        
        if self.use_colors:
            # Add color to the level name
            color = self.COLORS.get(record_copy.levelno, '')
            if color:
                record_copy.levelname = f"{color}{record_copy.levelname}{self.RESET}"
        
        return super().format(record_copy)


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for machine-readable logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log message
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'module': record.module,
            'line': record.lineno,
        }
        
        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        try:
            return json.dumps(log_entry, default=str, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            # Fallback to simple format if JSON serialization fails
            return f"JSON_FORMAT_ERROR: {record.getMessage()} (Error: {e})"


class SaiLogger:
    """Enhanced logger for SAI CLI tool with structured logging capabilities."""
    
    def __init__(self, name: str, config: Optional[SaiConfig] = None):
        """Initialize the SAI logger.
        
        Args:
            name: Logger name (typically __name__)
            config: SAI configuration object
        """
        self.name = name
        self.config = config or SaiConfig()
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self) -> None:
        """Setup the logger with appropriate handlers and formatters."""
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Set log level
        log_level = getattr(logging, self.config.log_level.value.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(log_level)
        console_formatter = self._get_formatter(LogFormat.STANDARD)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if log file is configured
        if self.config.log_file:
            self._setup_file_handler()
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def _setup_file_handler(self) -> None:
        """Setup file handler for logging to file."""
        try:
            log_file = Path(self.config.log_file).expanduser().resolve()
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Use rotating file handler to prevent log files from growing too large
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            
            file_level = getattr(logging, self.config.log_level.value.upper(), logging.INFO)
            file_handler.setLevel(file_level)
            
            # Use JSON format for file logs for better parsing
            file_formatter = self._get_formatter(LogFormat.JSON)
            file_handler.setFormatter(file_formatter)
            
            self.logger.addHandler(file_handler)
            
        except Exception as e:
            # If file logging fails, log to console but don't crash
            self.logger.warning(f"Failed to setup file logging: {e}")
    
    def _get_formatter(self, format_type: LogFormat) -> logging.Formatter:
        """Get formatter based on format type.
        
        Args:
            format_type: Type of formatter to create
            
        Returns:
            Configured logging formatter
        """
        if format_type == LogFormat.JSON:
            return JsonFormatter()
        elif format_type == LogFormat.DETAILED:
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        elif format_type == LogFormat.MINIMAL:
            return logging.Formatter('%(levelname)s: %(message)s')
        else:  # STANDARD
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message with optional extra context."""
        self.logger.debug(message, extra=extra or {})
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log info message with optional extra context."""
        self.logger.info(message, extra=extra or {})
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message with optional extra context."""
        self.logger.warning(message, extra=extra or {})
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, 
              exc_info: bool = False) -> None:
        """Log error message with optional extra context and exception info."""
        self.logger.error(message, extra=extra or {}, exc_info=exc_info)
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None,
                 exc_info: bool = False) -> None:
        """Log critical message with optional extra context and exception info."""
        self.logger.critical(message, extra=extra or {}, exc_info=exc_info)
    
    def log_execution_start(self, action: str, software: str, provider: str,
                           context: Optional[Dict[str, Any]] = None) -> None:
        """Log the start of an action execution.
        
        Args:
            action: Action being executed
            software: Software being acted upon
            provider: Provider being used
            context: Additional context information
        """
        extra = {
            'event_type': 'execution_start',
            'action': action,
            'software': software,
            'provider': provider,
            'timestamp': datetime.utcnow().isoformat(),
            **(context or {})
        }
        self.info(f"Starting execution: {action} {software} using {provider}", extra=extra)
    
    def log_execution_end(self, action: str, software: str, provider: str,
                         success: bool, execution_time: float,
                         context: Optional[Dict[str, Any]] = None) -> None:
        """Log the end of an action execution.
        
        Args:
            action: Action that was executed
            software: Software that was acted upon
            provider: Provider that was used
            success: Whether execution was successful
            execution_time: Time taken for execution in seconds
            context: Additional context information
        """
        extra = {
            'event_type': 'execution_end',
            'action': action,
            'software': software,
            'provider': provider,
            'success': success,
            'execution_time': execution_time,
            'timestamp': datetime.utcnow().isoformat(),
            **(context or {})
        }
        
        status = "completed successfully" if success else "failed"
        message = f"Execution {status}: {action} {software} using {provider} ({execution_time:.2f}s)"
        
        if success:
            self.info(message, extra=extra)
        else:
            self.error(message, extra=extra)
    
    def log_command_execution(self, command: str, exit_code: int, 
                             execution_time: float, stdout: Optional[str] = None,
                             stderr: Optional[str] = None) -> None:
        """Log command execution details.
        
        Args:
            command: Command that was executed
            exit_code: Exit code of the command
            execution_time: Time taken for execution in seconds
            stdout: Standard output (truncated for logging)
            stderr: Standard error (truncated for logging)
        """
        extra = {
            'event_type': 'command_execution',
            'command': command,
            'exit_code': exit_code,
            'execution_time': execution_time,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Truncate output for logging (keep first and last parts)
        if stdout:
            extra['stdout_length'] = len(stdout)
            if len(stdout) > 1000:
                extra['stdout_preview'] = stdout[:500] + "..." + stdout[-500:]
            else:
                extra['stdout_preview'] = stdout
        
        if stderr:
            extra['stderr_length'] = len(stderr)
            if len(stderr) > 1000:
                extra['stderr_preview'] = stderr[:500] + "..." + stderr[-500:]
            else:
                extra['stderr_preview'] = stderr
        
        success = exit_code == 0
        message = f"Command {'succeeded' if success else 'failed'}: {command} (exit: {exit_code}, time: {execution_time:.2f}s)"
        
        if success:
            self.debug(message, extra=extra)
        else:
            self.warning(message, extra=extra)
    
    def log_provider_detection(self, provider: str, available: bool, 
                              detection_time: float, details: Optional[Dict[str, Any]] = None) -> None:
        """Log provider detection results.
        
        Args:
            provider: Provider name
            available: Whether provider is available
            detection_time: Time taken for detection in seconds
            details: Additional detection details
        """
        extra = {
            'event_type': 'provider_detection',
            'provider': provider,
            'available': available,
            'detection_time': detection_time,
            'timestamp': datetime.utcnow().isoformat(),
            **(details or {})
        }
        
        status = "available" if available else "not available"
        message = f"Provider detection: {provider} is {status} ({detection_time:.3f}s)"
        
        self.debug(message, extra=extra)
    
    def log_cache_operation(self, operation: str, cache_type: str, key: str,
                           hit: Optional[bool] = None, details: Optional[Dict[str, Any]] = None) -> None:
        """Log cache operations.
        
        Args:
            operation: Cache operation (get, set, clear, etc.)
            cache_type: Type of cache (provider, saidata, etc.)
            key: Cache key
            hit: Whether it was a cache hit (for get operations)
            details: Additional operation details
        """
        extra = {
            'event_type': 'cache_operation',
            'operation': operation,
            'cache_type': cache_type,
            'key': key,
            'timestamp': datetime.utcnow().isoformat(),
            **(details or {})
        }
        
        if hit is not None:
            extra['cache_hit'] = hit
        
        message = f"Cache {operation}: {cache_type}[{key}]"
        if hit is not None:
            message += f" ({'hit' if hit else 'miss'})"
        
        self.debug(message, extra=extra)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON formatted log message
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                              'filename', 'module', 'lineno', 'funcName', 'created',
                              'msecs', 'relativeCreated', 'thread', 'threadName',
                              'processName', 'process', 'getMessage', 'exc_info',
                              'exc_text', 'stack_info']:
                    log_entry[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        try:
            return json.dumps(log_entry, default=str, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            # Fallback to simple format if JSON serialization fails
            return f"JSON_FORMAT_ERROR: {record.getMessage()} (Error: {e})"


def get_logger(name: str, config: Optional[SaiConfig] = None) -> Union[SaiLogger, logging.Logger]:
    """Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        config: SAI configuration object
        
    Returns:
        Configured logger instance (SaiLogger if config provided, regular Logger otherwise)
    """
    if config is not None:
        return SaiLogger(name, config)
    else:
        # For backward compatibility, return regular logger when no config provided
        # Ensure name has sai prefix
        if not name.startswith('sai.') and name != 'sai':
            name = f'sai.{name}'
        return logging.getLogger(name)


def get_log_level_from_string(level: Union[str, LogLevel]) -> int:
    """Convert string or LogLevel enum to logging level constant.
    
    Args:
        level: Log level as string or LogLevel enum
        
    Returns:
        Logging level constant
        
    Raises:
        ValueError: If level string is invalid
    """
    if isinstance(level, LogLevel):
        level = level.value
    
    level_str = str(level).upper()
    
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'WARN': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    
    if level_str not in level_map:
        raise ValueError(f"Invalid log level: {level}")
    
    return level_map[level_str]


def configure_logger(name: str, level: int, add_console_handler: bool = True,
                    log_file: Optional[Path] = None) -> logging.Logger:
    """Configure a specific logger with handlers and formatters.
    
    Args:
        name: Logger name
        level: Logging level
        add_console_handler: Whether to add console handler
        log_file: Optional log file path
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    if add_console_handler:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = StructuredFormatter()
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def setup_root_logging(config: SaiConfig, verbose: bool = False) -> None:
    """Setup root logging configuration for the entire application.
    
    Args:
        config: SAI configuration object
        verbose: Whether to enable verbose logging
    """
    # Override log level if verbose is requested
    if verbose:
        config.log_level = LogLevel.DEBUG
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Set log level
    log_level = getattr(logging, config.log_level.value.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Console handler with appropriate format
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    
    # Use simpler format for console output
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if configured
    if config.log_file:
        try:
            log_file = Path(config.log_file).expanduser().resolve()
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(log_level)
            
            # Use detailed format for file logs
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            # Log to console if file setup fails
            console_handler.stream.write(f"Warning: Failed to setup file logging: {e}\n")
    
    # Set logging level for third-party libraries to reduce noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('jsonschema').setLevel(logging.WARNING)