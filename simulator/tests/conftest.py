import pytest
from starlette.testclient import TestClient

from app.main import app
from app.services.state_service import simulator_state_service


@pytest.fixture(autouse=True)
def reset_simulator_state():
    """Ensure every test begins and ends with a clean, healthy simulator state."""
    simulator_state_service.reset()
    yield
    simulator_state_service.reset()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client
