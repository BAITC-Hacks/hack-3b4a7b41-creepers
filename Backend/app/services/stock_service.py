from app.core.errors import AppError
from app.schemas.product import Product
from app.services.product_service import ProductService


class StockService:
    def __init__(self, products: ProductService):
        self.products = products

    async def current(self, product_id: str) -> Product:
        return await self.products.detail(product_id)

    @staticmethod
    def ensure_available(product: Product, quantity: int):
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0 or quantity > 1000000:
            raise AppError("invalid_quantity", "Количество должно быть целым числом от 1 до 1000000.", 422)
        if product.stock is None:
            raise AppError("stock_unknown", "Остаток неизвестен. Добавление невозможно до уточнения наличия.", 409)
        if quantity > product.stock:
            raise AppError("insufficient_stock", "Недостаточно товара с учётом количества в корзине.", 409)
