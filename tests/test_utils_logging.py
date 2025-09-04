"""Tests for logging utilities."""

import logging
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from sai.utils.logging import (
    get_logger,
    setup_root_logging,
    ColoredFormatter,
    StructuredFormatter,
    get_log_level_from_string,
    configure_logger
)
from sai.models.config import SaiConfig, LogLevel


class TestLoggerUtils:
    """Test logger utility functions."""
    
    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger("test_module")
        
        assert isinstance(logger, logging.Logger)
        assert logger.name == "sai.test_module"
    
    def test_get_logger_with_sai_prefix(self):
        """Test getting logger that already has sai prefix."""
        logger = get_logger("sai.test_module")
        
        assert logger.name == "sai.test_module"
    
    def test_get_log_level_from_string(self):
        """Test converting string to log level."""
        assert get_log_level_from_string("debug") == logging.DEBUG
        assert get_log_level_from_string("info") == logging.INFO
        assert get_log_level_from_string("warning") == logging.WARNING
        assert get_log_level_from_string("error") == logging.ERROR
        
        # Test case insensitive
        assert get_log_level_from_string("DEBUG") == logging.DEBUG
        assert get_log_level_from_string("Info") == logging.INFO
    
    def test_get_log_level_from_string_invalid(self):
        """Test converting invalid string to log level."""
        with pytest.raises(ValueError, match="Invalid log level"):
            get_log_level_from_string("invalid")
    
    def test_get_log_level_from_enum(self):
        """Test converting LogLevel enum to log level."""
        assert get_log_level_from_string(LogLevel.DEBUG) == logging.DEBUG
        assert get_log_level_from_string(LogLevel.INFO) == logging.INFO
        assert get_log_level_from_string(LogLevel.WARNING) == logging.WARNING
        assert get_log_level_from_string(LogLevel.ERROR) == logging.ERROR


class TestColoredFormatter:
    """Test ColoredFormatter functionality."""
    
    def test_colored_formatter_creation(self):
        """Test colored formatter creation."""
        formatter = ColoredFormatter()
        
        assert isinstance(formatter, logging.Formatter)
        assert hasattr(formatter, 'COLORS')
        assert hasattr(formatter, 'RESET')
    
    def test_colored_formatter_format_info(self):
        """Test formatting INFO level message."""
        formatter = ColoredFormatter(use_colors=True)
        
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        
        # Should contain the message
        assert "Test message" in result
        # Should contain color codes for INFO level
        assert formatter.COLORS.get(logging.INFO, '') in result or result.endswith(formatter.RESET)
    
    def test_colored_formatter_format_error(self):
        """Test formatting ERROR level message."""
        formatter = ColoredFormatter(use_colors=True)
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Error message",
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        
        assert "Error message" in result
        # Should contain color codes for ERROR level
        assert formatter.COLORS.get(logging.ERROR, '') in result or result.endswith(formatter.RESET)
    
    def test_colored_formatter_no_color_support(self):
        """Test colored formatter when colors are not supported."""
        with patch('sai.utils.logging.sys.stdout.isatty', return_value=False):
            formatter = ColoredFormatter()
            
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="Test message",
                args=(),
                exc_info=None
            )
            
            result = formatter.format(record)
            
            # Should not contain color codes when not supported
            assert "Test message" in result
            # Check that no ANSI color codes are present
            assert '\033[' not in result


class TestStructuredFormatter:
    """Test StructuredFormatter functionality."""
    
    def test_structured_formatter_creation(self):
        """Test structured formatter creation."""
        formatter = StructuredFormatter()
        
        assert isinstance(formatter, logging.Formatter)
    
    def test_structured_formatter_format(self):
        """Test structured formatter output."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="sai.test",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = formatter.format(record)
        
        # Should be valid JSON
        import json
        data = json.loads(result)
        
        assert data['level'] == 'INFO'
        assert data['message'] == 'Test message'
        assert data['logger'] == 'sai.test'
        assert data['module'] == 'file'
        assert data['line'] == 42
        assert 'timestamp' in data
    
    def test_structured_formatter_with_extra_fields(self):
        """Test structured formatter with extra fields."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="sai.test",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Add extra fields
        record.user_id = "12345"
        record.request_id = "req-abc-123"
        
        result = formatter.format(record)
        
        import json
        data = json.loads(result)
        
        assert data['user_id'] == "12345"
        assert data['request_id'] == "req-abc-123"


class TestLoggingSetup:
    """Test logging setup functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Clear sai loggers
        sai_logger = logging.getLogger('sai')
        for handler in sai_logger.handlers[:]:
            sai_logger.removeHandler(handler)
    
    def test_setup_root_logging_console_only(self):
        """Test setting up root logging with console only."""
        config = SaiConfig(
            log_level=LogLevel.INFO,
            log_file=None
        )
        
        setup_root_logging(config, verbose=False)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        
        # Should have console handler
        console_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) > 0
    
    def test_setup_root_logging_with_file(self):
        """Test setting up root logging with file output."""
        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as temp_file:
            log_file = Path(temp_file.name)
        
        try:
            config = SaiConfig(
                log_level=LogLevel.DEBUG,
                log_file=log_file
            )
            
            setup_root_logging(config, verbose=True)
            
            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG
            
            # Should have both console and file handlers
            console_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
            file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.FileHandler)]
            
            assert len(console_handlers) > 0
            assert len(file_handlers) > 0
        finally:
            log_file.unlink(missing_ok=True)
    
    def test_setup_root_logging_verbose_mode(self):
        """Test setting up root logging in verbose mode."""
        config = SaiConfig(log_level=LogLevel.WARNING)
        
        setup_root_logging(config, verbose=True)
        
        root_logger = logging.getLogger()
        # Verbose mode should override config and use DEBUG
        assert root_logger.level == logging.DEBUG
    
    def test_configure_logger(self):
        """Test configuring individual logger."""
        logger_name = "sai.test_module"
        
        configure_logger(logger_name, logging.INFO, add_console_handler=True)
        
        logger = logging.getLogger(logger_name)
        assert logger.level == logging.INFO
        
        # Should have console handler
        console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) > 0
    
    def test_configure_logger_with_file(self):
        """Test configuring logger with file handler."""
        with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as temp_file:
            log_file = Path(temp_file.name)
        
        try:
            logger_name = "sai.test_module"
            
            configure_logger(
                logger_name, 
                logging.DEBUG, 
                add_console_handler=True,
                log_file=log_file
            )
            
            logger = logging.getLogger(logger_name)
            assert logger.level == logging.DEBUG
            
            # Should have both handlers
            console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
            file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
            
            assert len(console_handlers) > 0
            assert len(file_handlers) > 0
        finally:
            log_file.unlink(missing_ok=True)


class TestLoggingIntegration:
    """Integration tests for logging functionality."""
    
    def test_logger_hierarchy(self):
        """Test logger hierarchy and inheritance."""
        # Configure parent logger
        parent_logger = get_logger("parent")
        parent_logger.setLevel(logging.INFO)
        
        # Child logger should inherit settings
        child_logger = get_logger("parent.child")
        
        # Both should be under sai namespace
        assert parent_logger.name == "sai.parent"
        assert child_logger.name == "sai.parent.child"
    
    def test_logging_with_different_levels(self):
        """Test logging with different log levels."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.log', delete=False) as temp_file:
            log_file = Path(temp_file.name)
        
        try:
            config = SaiConfig(
                log_level=LogLevel.INFO,
                log_file=log_file
            )
            
            setup_root_logging(config, verbose=False)
            
            logger = get_logger("test_module")
            
            # Log messages at different levels
            logger.debug("Debug message")  # Should not appear
            logger.info("Info message")    # Should appear
            logger.warning("Warning message")  # Should appear
            logger.error("Error message")  # Should appear
            
            # Read log file
            log_content = log_file.read_text()
            
            assert "Debug message" not in log_content
            assert "Info message" in log_content
            assert "Warning message" in log_content
            assert "Error message" in log_content
        finally:
            log_file.unlink(missing_ok=True)
    
    def test_structured_logging_output(self):
        """Test structured logging output format."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.log', delete=False) as temp_file:
            log_file = Path(temp_file.name)
        
        try:
            # Configure with structured formatter
            logger = get_logger("test_module")
            handler = logging.FileHandler(log_file)
            handler.setFormatter(StructuredFormatter())
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            
            logger.info("Test structured message", extra={"user_id": "123", "action": "test"})
            
            # Read and parse log file
            log_content = log_file.read_text().strip()
            
            import json
            log_data = json.loads(log_content)
            
            assert log_data['message'] == "Test structured message"
            assert log_data['user_id'] == "123"
            assert log_data['action'] == "test"
            assert log_data['level'] == "INFO"
        finally:
            log_file.unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__])