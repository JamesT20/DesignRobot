import logging
import queue
import threading

# Module-level loggers
logger_network = logging.getLogger("network")
logger_core = logging.getLogger("core")
logger_ui = logging.getLogger("ui")

# Root logger
root_logger = logging.getLogger()

# Shared queue for UI display (thread-safe)
_log_queue = None


class QueueHandler(logging.Handler):
    """Custom handler that puts log records on a queue for async display."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            level = record.levelname
            self.log_queue.put_nowait((msg, level))
        except Exception:
            self.handleError(record)


def init_logging(log_queue):
    """Initialize logging system with UI queue output (no file persistence)."""
    global _log_queue
    _log_queue = log_queue

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Set root logger to DEBUG
    root_logger.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s][%(name)s] %(message)s",
        datefmt="%H:%M:%S"
    )

    # Add queue handler (for UI display)
    queue_handler = QueueHandler(log_queue)
    queue_handler.setLevel(logging.INFO)
    queue_handler.setFormatter(formatter)
    root_logger.addHandler(queue_handler)

    # Optional: add console handler for debugging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    # Uncomment if you want console output during development
    # root_logger.addHandler(console_handler)


def get_logger(name):
    """Get a named logger."""
    return logging.getLogger(name)
