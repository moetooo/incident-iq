import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any, Dict


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "payment-api",
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "scenario"):
            log_obj["scenario"] = record.scenario
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_obj.update(record.extra_data)
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configures structured root logger."""
    logger = logging.getLogger("simulator")
    logger.setLevel(level)
    
    # Avoid duplicate handlers if reinitialized
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        
    return logger


logger = setup_logging()
