"""Shared pytest fixtures.

The environment is configured before the application modules are imported so
that the cached settings object picks up the test configuration.
"""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["GEMINI_API_KEY"] = ""
os.environ["LLM_ENABLED"] = "true"
os.environ["API_KEY"] = ""
os.environ["SIMULATOR_BASE_URL"] = "http://simulator.test:8001"
os.environ["LOG_LEVEL"] = "WARNING"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.api.deps import get_fallback_orchestrator, get_simulator_client
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.investigation.deterministic import DeterministicEngine  # noqa: E402
from app.investigation.llm.base import AnalysisRequest, LLMProvider, LLMProviderError  # noqa: E402
from app.investigation.llm.model_fallback import AttemptRecord, FallbackResult  # noqa: E402
from app.main import create_app  # noqa: E402


class FakeSimulatorClient:
    """Simulator double used by the API tests."""

    def __init__(
        self,
        evidence: list[dict] | None = None,
        deployments: list[dict] | None = None,
        *,
        healthy: bool = True,
        unavailable: bool = False,
        remediation_response: dict | None = None,
    ) -> None:
        self.evidence = evidence or []
        self.deployments = deployments or []
        self.healthy = healthy
        self.unavailable = unavailable
        self.remediation_response = remediation_response or {
            "status": "success",
            "message": "Applied",
            "details": {},
        }
        self.executed: list[dict] = []

    def health(self, timeout: float | None = None) -> bool:
        return self.health_status(timeout) == "ok"

    def health_status(self, timeout: float | None = None) -> str:
        if self.unavailable:
            return "unreachable"
        return "ok" if self.healthy else "degraded"

    def fetch_evidence(self, scenario_id: str | None = None) -> list[dict]:
        if self.unavailable:
            raise RuntimeError("simulator unavailable")
        return list(self.evidence)

    def fetch_deployments(self) -> list[dict]:
        if self.unavailable:
            raise RuntimeError("simulator unavailable")
        return list(self.deployments)

    def execute_remediation(self, **kwargs) -> dict:
        if self.unavailable:
            raise RuntimeError("simulator unavailable")
        self.executed.append(kwargs)
        return dict(self.remediation_response)


class FakeProvider(LLMProvider):
    """LLM provider double."""

    name = "gemini"
    model = "gemini-test-model"

    def __init__(self, report=None, error: Exception | None = None) -> None:
        self.report = report
        self.error = error
        self.requests: list[AnalysisRequest] = []

    def analyze(self, request: AnalysisRequest):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        if callable(self.report):
            return self.report(request)
        return self.report


class FakeOrchestrator:
    """Test double for GeminiFallbackOrchestrator wrapping a FakeProvider."""

    def __init__(self, provider: FakeProvider | None = None) -> None:
        self.provider = provider or FakeProvider()
        self.calls: list[tuple] = []

    async def analyze(self, request: AnalysisRequest, primary_model: str) -> FallbackResult:
        self.calls.append((request, primary_model))
        model = getattr(self.provider, "model", primary_model)
        try:
            report = self.provider.analyze(request)
        except LLMProviderError as exc:
            report = DeterministicEngine().analyze(request)
            return FallbackResult(
                report=report,
                provider_name="deterministic",
                model=None,
                llm_used=False,
                attempts=[
                    AttemptRecord(
                        model=primary_model,
                        attempt_number=1,
                        duration_ms=1,
                        success=False,
                        reason=exc.reason,
                    )
                ],
                fallback_used=True,
            )
        return FallbackResult(
            report=report,
            provider_name="gemini",
            model=model,
            llm_used=True,
            attempts=[
                AttemptRecord(
                    model=model,
                    attempt_number=1,
                    duration_ms=1,
                    success=True,
                    reason=None,
                )
            ],
            fallback_used=False,
        )


@pytest.fixture(scope="session")
def engine():
    """Create an in-memory database shared by the whole test session."""
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(bind=test_engine)
    return test_engine


@pytest.fixture(autouse=True)
def clean_database(engine):
    """Remove every row before each test."""
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    yield


@pytest.fixture
def session(engine):
    """Return a database session bound to the test database."""
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db_session = factory()
    try:
        yield db_session
    finally:
        db_session.rollback()
        db_session.close()


@pytest.fixture
def simulator_client():
    """Return the default simulator double."""
    return FakeSimulatorClient()


@pytest.fixture
def make_client(engine):
    """Return a factory that builds a test client with custom overrides."""
    from app.api.deps import get_provider_factory

    def _factory(
        simulator=None, provider_factory=None, orchestrator=None
    ) -> TestClient:
        application = create_app()
        factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

        def override_get_db():
            db_session = factory()
            try:
                yield db_session
            finally:
                db_session.close()

        application.dependency_overrides[get_db] = override_get_db
        application.dependency_overrides[get_simulator_client] = (
            lambda: simulator or FakeSimulatorClient()
        )
        if provider_factory is not None:
            application.dependency_overrides[get_provider_factory] = lambda: provider_factory
        if orchestrator is not None:
            application.dependency_overrides[get_fallback_orchestrator] = lambda: orchestrator
        return TestClient(application)

    return _factory


@pytest.fixture
def app(engine, simulator_client):
    """Build the application with test overrides."""
    application = create_app()
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db_session = factory()
        try:
            yield db_session
        finally:
            db_session.close()

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_simulator_client] = lambda: simulator_client
    return application


@pytest.fixture
def client(app):
    """Return a test client for the application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def incident_payload() -> dict:
    """Return a valid incident creation payload."""
    return {
        "title": "Payment API timeouts",
        "service": "payment-api",
        "severity": "high",
        "description": "Payment requests are timing out",
    }
