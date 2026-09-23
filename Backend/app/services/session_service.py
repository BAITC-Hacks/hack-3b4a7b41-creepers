import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from decimal import Decimal

from app.config import Settings
from app.core.errors import AppError
from app.schemas.cart import CartItem
from app.schemas.product import Product
from app.schemas.procurement import ProcurementReport


@dataclass
class PendingCartAction:
    session_id: str
    product_id: str
    article: str | None
    quantity: int
    current_stock: Decimal
    created_at: float = field(default_factory=time.monotonic)


@dataclass
class Session:
    session_id: str
    last_product: Product | None = None
    recent_products: list[Product] = field(default_factory=list)
    pending_cart_action: PendingCartAction | None = None
    cart: dict[str, CartItem] = field(default_factory=dict)
    touched_at: float = field(default_factory=time.monotonic)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    users: int = 0
    last_query: str = ""
    language: str = "ru"
    procurement: ProcurementReport | None = None
    photo_candidates: list[Product] = field(default_factory=list)


class SessionService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sessions: dict[str, Session] = {}

    @asynccontextmanager
    async def use(self, session_id: str, *, create: bool = True):
        now = time.monotonic()
        for key, session in list(self.sessions.items()):
            if session.users == 0 and now - session.touched_at > self.settings.session_ttl_seconds:
                del self.sessions[key]
        session = self.sessions.get(session_id)
        if session is None:
            if not create:
                raise AppError("session_not_found", "Сессия не найдена или истекла.", 404)
            if len(self.sessions) >= self.settings.max_sessions:
                raise AppError("session_capacity", "Сервис занят. Повторите запрос позже.", 503)
            session = Session(session_id=session_id)
            self.sessions[session_id] = session
        # Count queued operations too, so cleanup cannot create a second lock.
        session.users += 1
        try:
            async with session.lock:
                session.touched_at = time.monotonic()
                yield session
        finally:
            session.users -= 1
            session.touched_at = time.monotonic()

    def remember(self, session: Session, products: list[Product]):
        selected = products[0] if len(products) == 1 else None
        if session.pending_cart_action and (
            selected is None or selected.id != session.pending_cart_action.product_id
        ):
            session.pending_cart_action = None
        session.recent_products = products[:20]
        session.last_product = selected

    def selected(self, session: Session, product_id: str | None = None) -> str:
        if product_id:
            return product_id
        if session.last_product:
            return session.last_product.id
        raise AppError("product_selection_required", "Укажите ID товара: например, «товар 515291».", 409)
