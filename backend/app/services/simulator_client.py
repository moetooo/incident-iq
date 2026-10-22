"""HTTP client for the production simulator."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.errors import SimulatorUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)


class SimulatorClient:
    """Reads telemetry and applies simulated remediations.

    The simulator is reached over HTTP only. The backend never writes to the
    simulator's storage and never assumes it is available.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self.base_url, timeout=self.timeout)
        return self._client

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def health(self, timeout: float | None = None) -> bool:
        """Return True when the simulator is reachable and reports a healthy state."""
        return self.health_status(timeout=timeout) == "ok"

    def health_status(self, timeout: float | None = None) -> str:
        """Return the simulator health state.

        Returns ``"ok"`` when the simulator is reachable and reports a healthy
        service, ``"degraded"`` when it is reachable but reports an unhealthy
        service, and ``"unreachable"`` when it cannot be contacted.

        The HTTP status code alone is not enough: the simulator answers ``200``
        with ``{"status": "degraded", "healthy": false}`` while it is serving
        a failed scenario.
        """
        try:
            response = self._get_client().get("/health", timeout=timeout or self.timeout)
        except httpx.HTTPError as exc:
            logger.warning("simulator_health_check_failed", extra={"error": str(exc)})
            return "unreachable"

        if response.status_code != 200:
            return "unreachable"

        payload: Any = None
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if not isinstance(payload, dict):
            return "ok"

        if "healthy" in payload:
            return "ok" if bool(payload["healthy"]) else "degraded"

        status = str(payload.get("status", "")).strip().lower()
        if status:
            return "ok" if status in {"ok", "healthy", "up"} else "degraded"

        return "ok"

    def fetch_evidence(self, scenario_id: str | None = None) -> list[dict[str, Any]]:
        """Return the evidence produced by the simulator."""
        params = {"scenario_id": scenario_id} if scenario_id else None
        payload = self._request("GET", "/internal/evidence", params=params)
        return _extract_items(payload, ("items", "evidence", "results"))

    def fetch_deployments(self) -> list[dict[str, Any]]:
        """Return the recent deployment events of the simulator."""
        payload = self._request("GET", "/internal/deployments")
        return _extract_items(payload, ("items", "deployments", "results"))

    def execute_remediation(
        self,
        *,
        action: str,
        parameters: dict[str, Any],
        incident_id: str,
        remediation_id: str,
    ) -> dict[str, Any]:
        """Ask the simulator to apply an allowlisted simulated remediation."""
        payload = self._request(
            "POST",
            "/internal/remediations",
            json={
                "action": action,
                "parameters": parameters,
                "incident_id": incident_id,
                "remediation_id": remediation_id,
            },
        )
        if isinstance(payload, dict):
            return payload
        return {"status": "success", "message": str(payload)}

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        try:
            response = self._get_client().request(method, path, params=params, json=json)
        except httpx.HTTPError as exc:
            raise SimulatorUnavailableError(
                f"The simulator is unreachable: {exc}",
                details={"path": path, "error": str(exc)},
            ) from exc

        if response.status_code >= 400:
            raise SimulatorUnavailableError(
                f"The simulator returned HTTP {response.status_code} for {path}",
                details={"path": path, "status_code": response.status_code},
            )

        if not response.content:
            return {}

        try:
            return response.json()
        except ValueError as exc:
            raise SimulatorUnavailableError(
                f"The simulator returned a non-JSON response for {path}",
                details={"path": path},
            ) from exc


def _extract_items(payload: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    """Return the list of items from a simulator payload.

    The simulator may return the list directly or wrap it in one of the given
    keys. Items that are not objects are ignored.
    """
    items: Any = None
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        for key in keys:
            if isinstance(payload.get(key), list):
                items = payload[key]
                break
        else:
            # Fall back to the first list value in the payload.
            for value in payload.values():
                if isinstance(value, list):
                    items = value
                    break

    if not isinstance(items, list):
        return []

    return [item for item in items if isinstance(item, dict)]
