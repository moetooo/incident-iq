from fastapi import APIRouter
from app.models.payment import PaymentRequest, PaymentResponse
from app.services.state_service import simulator_state_service

router = APIRouter(prefix="/payments", tags=["Payment Service API"])


@router.post("", response_model=PaymentResponse)
def process_payment(request: PaymentRequest) -> PaymentResponse:
    """Processes a simulated payment transaction.
    
    Behavior depends on active scenario:
    - normal: 200 OK with fast response time.
    - database_failure: 503 Service Unavailable (pool exhausted).
    - payment_timeout: 504 Gateway Timeout.
    - bad_deployment: 500 Internal Server Error (NullPointerException).
    """
    return simulator_state_service.process_payment(request)
