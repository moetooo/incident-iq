"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from fastapi import Depends, Header

from app.core.config import Settings, get_settings
from app.core.errors import UnauthorizedError, ValidationError
from app.investigation.deterministic import DeterministicEngine
from app.investigation.llm.base import LLMProvider
from app.investigation.llm.gemini_provider import GeminiProvider
from app.repositories.evidence_repository import EvidenceRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.investigation_repository import InvestigationRepository
from app.repositories.remediation_repository import RemediationRepository
from app.services.evidence_service import EvidenceService
from app.services.incident_service import IncidentService
from app.services.investigation_service import InvestigationService
from app.services.remediation_dispatcher import RemediationDispatcher
from app.services.remediation_service import RemediationService
from app.services.simulator_client import SimulatorClient

ProviderFactory = Callable[[], LLMProvider | None]


def settings_dependency() -> Settings:
    """Return the application settings."""
    return get_settings()


@lru_cache(maxsize=1)
def _simulator_client() -> SimulatorClient:
    settings = get_settings()
    return SimulatorClient(settings.SIMULATOR_BASE_URL, settings.SIMULATOR_TIMEOUT_SECONDS)


def get_simulator_client() -> SimulatorClient:
    """Return the shared simulator HTTP client."""
    return _simulator_client()


def get_incident_repository() -> IncidentRepository:
    """Return the incident repository."""
    return IncidentRepository()


def get_evidence_repository() -> EvidenceRepository:
    """Return the evidence repository."""
    return EvidenceRepository()


def get_investigation_repository() -> InvestigationRepository:
    """Return the investigation repository."""
    return InvestigationRepository()


def get_remediation_repository() -> RemediationRepository:
    """Return the remediation repository."""
    return RemediationRepository()


def get_incident_service(
    repository: IncidentRepository = Depends(get_incident_repository),
) -> IncidentService:
    """Return the incident service."""
    return IncidentService(repository)


def get_evidence_service(
    simulator_client: SimulatorClient = Depends(get_simulator_client),
    repository: EvidenceRepository = Depends(get_evidence_repository),
) -> EvidenceService:
    """Return the evidence service."""
    return EvidenceService(simulator_client, repository)


def build_llm_provider() -> LLMProvider | None:
    """Create the configured provider, or ``None`` when no key is available."""
    settings = get_settings()
    if not settings.llm_configured:
        return None
    return GeminiProvider(
        api_key=settings.GEMINI_API_KEY,
        model=settings.GEMINI_MODEL,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
    )


def get_provider_factory() -> ProviderFactory:
    """Return the factory used to create the analysis provider."""
    return build_llm_provider


def get_investigation_service(
    evidence_service: EvidenceService = Depends(get_evidence_service),
    incident_repository: IncidentRepository = Depends(get_incident_repository),
    investigation_repository: InvestigationRepository = Depends(get_investigation_repository),
    remediation_repository: RemediationRepository = Depends(get_remediation_repository),
    provider_factory: ProviderFactory = Depends(get_provider_factory),
) -> InvestigationService:
    """Return the investigation service."""
    settings = get_settings()
    return InvestigationService(
        evidence_service=evidence_service,
        incident_repository=incident_repository,
        investigation_repository=investigation_repository,
        remediation_repository=remediation_repository,
        provider_factory=provider_factory,
        fallback_engine=DeterministicEngine(),
        max_evidence_items=settings.LLM_MAX_EVIDENCE_ITEMS,
    )


def get_remediation_dispatcher(
    simulator_client: SimulatorClient = Depends(get_simulator_client),
) -> RemediationDispatcher:
    """Return the remediation dispatcher."""
    return RemediationDispatcher(simulator_client)


def get_remediation_service(
    repository: RemediationRepository = Depends(get_remediation_repository),
    incident_repository: IncidentRepository = Depends(get_incident_repository),
    dispatcher: RemediationDispatcher = Depends(get_remediation_dispatcher),
) -> RemediationService:
    """Return the remediation service."""
    return RemediationService(
        remediation_repository=repository,
        incident_repository=incident_repository,
        dispatcher=dispatcher,
    )


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Enforce service authentication when an API key is configured."""
    settings = get_settings()
    if not settings.auth_required:
        return
    if not x_api_key or x_api_key != settings.API_KEY:
        raise UnauthorizedError("A valid X-API-Key header is required")


def require_operator(x_operator_id: str | None = Header(default=None)) -> str:
    """Require the identity of the human operator behind a decision."""
    operator_id = (x_operator_id or "").strip()
    if not operator_id:
        raise ValidationError(
            "The X-Operator-Id header is required for approval and rejection decisions",
            details={"header": "X-Operator-Id"},
        )
    return operator_id
