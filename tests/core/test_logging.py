"""Tests for logging functionality."""

import json
import logging
from pathlib import Path

import pytest

from feptm.core.log import LogContext, setup_logging


def test_json_log_format(tmp_path, caplog):
    """Test that logs are formatted as JSON."""
    # Setup logging with a temporary file
    log_file = tmp_path / "test.log"
    setup_logging(log_file=log_file)
    logger = logging.getLogger("test")

    # Log a test message
    test_message = "Test log message"
    logger.info(test_message)

    # Flush all handlers to ensure content is written
    for handler in logger.handlers + logging.getLogger().handlers:
        handler.flush()

    # Read the log file
    log_content = log_file.read_text()
    log_entry = json.loads(log_content.strip())

    # Verify JSON structure
    assert log_entry["message"] == test_message
    assert log_entry["level"] == "INFO"
    assert log_entry["logger"] == "test"
    assert "timestamp" in log_entry


def test_log_context(caplog):
    """Test that LogContext adds context to log messages."""
    logger = logging.getLogger("test")

    # Use LogContext to add extra fields
    with LogContext(user_id="123", action="test"):
        with caplog.at_level(logging.INFO):
            logger.info("Test message with context")

    # Verify that context was added
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert hasattr(record, "extra")
    assert record.extra["user_id"] == "123"
    assert record.extra["action"] == "test"


def test_log_rotation(tmp_path):
    """Test that log files are rotated correctly."""
    # Setup logging with a small max size
    log_file = tmp_path / "rotating.log"
    setup_logging(log_file=log_file)
    logger = logging.getLogger("test")

    # Generate messages large enough to trigger rotation
    test_message = "Test rotation message" + "x" * 5000  # Make message large enough
    for i in range(1000):  # Generate enough messages to trigger rotation
        logger.info(f"{test_message} {i}")

    # Flush all handlers to ensure content is written
    for handler in logger.handlers + logging.getLogger().handlers:
        handler.flush()

    # Check that rotation occurred
    assert log_file.exists()
    assert (log_file.parent / "rotating.log.1").exists()
    assert (log_file.parent / "rotating.log.5").exists()
    assert not (log_file.parent / "rotating.log.6").exists()
