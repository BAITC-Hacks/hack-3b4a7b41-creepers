import time
from urllib.parse import quote

from app.config import Settings
from app.core.errors import AppError
from app.schemas.cart import CartItem, CartResponse, PendingConfirmation
from app.services.session_service import PendingCartAction, Session
from app.services.stock_service import StockService


class CartService:
    """Call while holding SessionService.use(). All cart mutations live here."""

    def __init__(self, stock: StockService, settings: Settings):
        self.stock = stock
        self.settings = settings

    def view(self, session: Session) -> CartResponse:
        return CartResponse(
            items=[item.model_copy(deep=True) for item in session.cart.values()],
            total_items=sum(item.quantity for item in session.cart.values()),
            checkout_url=f"{self.settings.demo_checkout_base_url}/cart/{quote(session.session_id, safe='')}",
        )

    async def prepare(self, session: Session, product_id: str, quantity: int) -> PendingConfirmation:
        # A failed replacement must not leave an older action confirmable.
        session.pending_cart_action = None
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 1000000:
            raise AppError("invalid_quantity", "Количество должно быть целым числом от 1 до 1000000.", 422)
        product = await self.stock.current(product_id)
        existing = session.cart.get(product_id)
        total = quantity + (existing.quantity if existing else 0)
        self.stock.ensure_available(product, total)
        session.pending_cart_action = PendingCartAction(
            session_id=session.session_id, product_id=product.id,
            article=product.article, quantity=quantity, current_stock=product.stock,
        )
        return PendingConfirmation(
            product=product, quantity=quantity, available_stock=product.stock,
            message=f"Подтвердите добавление {quantity} шт. товара «{product.name}».",
        )

    async def confirm(self, session: Session) -> CartResponse:
        pending = session.pending_cart_action
        if pending is None:
            raise AppError("pending_action_missing", "Нет добавления, ожидающего подтверждения.", 409)
        if time.monotonic() - pending.created_at > 300:
            session.pending_cart_action = None
            raise AppError("pending_action_expired", "Подтверждение истекло. Подготовьте добавление заново.", 409)
        if pending.session_id != session.session_id:
            raise AppError("pending_action_invalid", "Подтверждение не относится к этой сессии.", 409)
        product = await self.stock.current(pending.product_id)
        existing = session.cart.get(product.id)
        quantity = pending.quantity + (existing.quantity if existing else 0)
        try:
            self.stock.ensure_available(product, pending.quantity)
            self.stock.ensure_available(product, quantity)
        except AppError:
            session.pending_cart_action = None
            raise
        # No await between mutation and clearing the pending action.
        session.cart[product.id] = CartItem(product=product, quantity=quantity)
        session.pending_cart_action = None
        return self.view(session)

    def cancel(self, session: Session) -> bool:
        cancelled = session.pending_cart_action is not None
        session.pending_cart_action = None
        return cancelled
