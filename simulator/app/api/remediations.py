from fastapi import APIRouter, HTTPException, status
from app.core.logging import logger
from app.core.errors import UnsupportedActionError, InvalidParametersError
from app.models.remediation import RemediationExecutionRequest, RemediationExecutionResponse
from app.services.state_service import simulator_state_service

router = APIRouter(prefix="/internal/remediations", tags=["Remediations"])


@router.post(
    "",
    response_model=RemediationExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute allowlisted simulated remediation action"
)
def execute_remediation(request: RemediationExecutionRequest) -> RemediationExecutionResponse:
    """Executes an allowlisted simulated remediation action against simulator state.
    
    Conforms to Canonical API Contract §6.1.
    """
    try:
        result = simulator_state_service.execute_remediation(
            action=request.action,
            parameters=request.parameters
        )
    except UnsupportedActionError as exc:
        logger.warning(
            f"Remediation action rejected: {exc.message}",
            extra={"extra_data": {"action": exc.action, "code": exc.code}}
        )
        raise HTTPException(
            status_code=422,
            detail={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        )
    except InvalidParametersError as exc:
        logger.warning(
            f"Remediation parameters rejected: {exc.message}",
            extra={"extra_data": {"action": request.action, "code": exc.code}}
        )
        raise HTTPException(
            status_code=422,
            detail={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        )

    return RemediationExecutionResponse(
        status=result["status"],
        message=result["message"],
        details=result.get("details", {})
    )
