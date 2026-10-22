"""Application error types and the canonical error response format."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for errors that map to a structured API response."""

    code = "INTERNAL_ERROR"
    status_code = 500

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}

    def to_payload(self, request_id: str) -> dict[str, Any]:
        """Return the error body used by the API."""
        error: dict[str, Any] = {
            "code": self.code,
            "message": self.message,
            "request_id": request_id,
        }
        if self.details:
            error["details"] = self.details
        return {"error": error}


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 422


class UnauthorizedError(AppError):
    code = "UNAUTHORIZED"
    status_code = 401


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    status_code = 403


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404


class ConflictError(AppError):
    code = "CONFLICT"
    status_code = 409


class UnsupportedActionError(AppError):
    code = "UNSUPPORTED_ACTION"
    status_code = 422


class InvalidParametersError(AppError):
    code = "INVALID_PARAMETERS"
    status_code = 422


class SimulatorUnavailableError(AppError):
    code = "SIMULATOR_UNAVAILABLE"
    status_code = 503
