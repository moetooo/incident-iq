"""Unit tests for the simulator HTTP client.

The HTTP transport is stubbed with ``httpx.MockTransport`` so the client logic
can be asserted without a running simulator.
"""

from __future__ import annotations

import httpx
import pytest

from app.core.errors import SimulatorUnavailableError
from app.services.simulator_client import SimulatorClient


def _client(handler) -> SimulatorClient:
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(
        base_url="http://simulator.test:8001", transport=transport, timeout=5.0
    )
    return SimulatorClient("http://simulator.test:8001", timeout=5.0, client=http_client)


def test_health_status_is_ok_for_a_healthy_service():
    client = _client(lambda request: httpx.Response(200, json={"status": "ok", "healthy": True}))

    assert client.health_status() == "ok"
    assert client.health() is True


def test_health_status_is_degraded_when_the_service_is_unhealthy():
    client = _client(
        lambda request: httpx.Response(
            200, json={"status": "degraded", "healthy": False, "scenario": "database_failure"}
        )
    )

    assert client.health_status() == "degraded"
    assert client.health() is False


def test_health_status_is_degraded_for_a_non_ok_status_string():
    client = _client(lambda request: httpx.Response(200, json={"status": "degraded"}))

    assert client.health_status() == "degraded"


def test_health_status_is_unreachable_on_a_server_error():
    client = _client(lambda request: httpx.Response(500, json={"status": "error"}))

    assert client.health_status() == "unreachable"
    assert client.health() is False


def test_health_status_is_unreachable_on_a_transport_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    client = _client(handler)

    assert client.health_status() == "unreachable"
    assert client.health() is False


def test_health_status_falls_back_to_ok_without_health_fields():
    client = _client(lambda request: httpx.Response(200, json={"ping": "pong"}))

    assert client.health_status() == "ok"


def test_fetch_evidence_accepts_the_items_envelope():
    client = _client(
        lambda request: httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "sim_1",
                        "type": "log",
                        "source": "payment-api",
                        "timestamp": "2026-01-01T10:00:00Z",
                        "summary": "boom",
                        "details": {},
                    }
                ]
            },
        )
    )

    items = client.fetch_evidence("database_failure")

    assert len(items) == 1
    assert items[0]["type"] == "log"


def test_fetch_evidence_accepts_the_evidence_envelope():
    client = _client(
        lambda request: httpx.Response(200, json={"evidence": [{"type": "metric"}]})
    )

    assert client.fetch_evidence() == [{"type": "metric"}]


def test_execute_remediation_returns_the_simulator_payload():
    client = _client(
        lambda request: httpx.Response(
            200, json={"status": "success", "message": "done", "details": {"restarted": True}}
        )
    )

    payload = client.execute_remediation(
        action="restart_demo_service",
        parameters={},
        incident_id="inc_1",
        remediation_id="rem_1",
    )

    assert payload["status"] == "success"
    assert payload["details"] == {"restarted": True}


def test_execute_remediation_raises_on_an_error_status():
    client = _client(lambda request: httpx.Response(422, json={"status": "failed"}))

    with pytest.raises(SimulatorUnavailableError):
        client.execute_remediation(
            action="restart_demo_service",
            parameters={},
            incident_id="inc_1",
            remediation_id="rem_1",
        )
