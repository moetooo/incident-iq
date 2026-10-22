from typing import Optional
from pydantic import BaseModel, Field


class PaymentRequest(BaseModel):
    amount: float = Field(gt=0, description="Payment transaction amount")
    currency: str = Field(default="USD", description="Currency code (e.g. USD, EUR)")
    payment_method: str = Field(default="credit_card", description="Payment method")
    customer_id: str = Field(default="cust_demo_01", description="Customer ID")
    simulate_delay_ms: Optional[int] = Field(default=None, description="Optional override for demo latency")


class PaymentResponse(BaseModel):
    transaction_id: str
    status: str
    amount: float
    currency: str
    latency_ms: float
    message: str
