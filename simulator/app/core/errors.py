"""Simulator error definitions conforming to canonical API contract."""

from typing import Any, Dict, List, Optional


class SimulatorError(Exception):
    """Base error for simulator operations."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class UnsupportedActionError(SimulatorError):
    """Raised when a requested remediation action is not on the server allowlist."""
    def __init__(self, action: str, allowed_actions: List[str]):
        message = f"Action '{action}' is not on the remediation allowlist"
        super().__init__(
            message=message,
            code="UNSUPPORTED_ACTION",
            details={"action": action, "allowed_actions": sorted(allowed_actions)}
        )
        self.action = action
        self.allowed_actions = allowed_actions


class InvalidParametersError(SimulatorError):
    """Raised when parameters for a remediation action fail validation."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="INVALID_PARAMETERS", details=details or {})
