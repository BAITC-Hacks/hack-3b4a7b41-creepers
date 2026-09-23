from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.schemas.product import Product

SessionId = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z0-9_-]{1,128}$")]
ProductId = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[\w.-]{1,200}$")]
Quantity = Annotated[int, Field(strict=True, gt=0, le=1000000)]


class SessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: SessionId


class CartPrepareRequest(SessionRequest):
    product_id: ProductId
    quantity: Quantity


class PendingConfirmation(BaseModel):
    pending_confirmation: bool = True
    product: Product
    quantity: int
    available_stock: Decimal
    message: str


class CartItem(BaseModel):
    product: Product
    quantity: int


class CartResponse(BaseModel):
    items: list[CartItem] = Field(default_factory=list)
    total_items: int = 0
    checkout_url: str


class CancelResponse(BaseModel):
    message: str = "Ожидающее добавление отменено."
    cancelled: bool
    cart: CartResponse
