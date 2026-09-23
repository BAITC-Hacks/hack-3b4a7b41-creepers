from typing import Annotated

from pydantic import Field, StringConstraints

from app.agents.intent import Intent
from app.core.errors import ErrorInfo
from app.schemas.cart import CartResponse, PendingConfirmation, SessionRequest
from app.schemas.product import Alternative, Product
from pydantic import BaseModel


class ChatRequest(SessionRequest):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class ChatResponse(BaseModel):
    message: str
    intent: Intent = "unknown"
    products: list[Product] = Field(default_factory=list)
    alternatives: list[Alternative] = Field(default_factory=list)
    pending_confirmation: PendingConfirmation | None = None
    cart: CartResponse | None = None
    checkout_url: str | None = None
    error: ErrorInfo | None = None
