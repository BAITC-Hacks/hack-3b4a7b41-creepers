"""Service facade: the classifier/assistant never mutates carts or sessions."""
from app.services.alternative_service import AlternativeService
from app.services.conditions_service import ConditionsService
from app.services.cart_service import CartService
from app.services.product_service import ProductService
from app.services.session_service import Session, SessionService


class AssistantTools:
    def __init__(self, products: ProductService, alternatives: AlternativeService, sessions: SessionService, cart: CartService):
        self.products = products
        self.alternatives = alternatives
        self.sessions = sessions
        self.cart = cart
        self.conditions = ConditionsService()

    async def search(self, session: Session, query: str):
        result = await self.products.search(query)
        self.sessions.remember(session, result.products)
        return result

    async def detail(self, session: Session, product_id: str | None):
        product = await self.products.detail(self.sessions.selected(session, product_id))
        self.sessions.remember(session, [product])
        return product
