import asyncio

from app.clients.ekt_client import EktClient
from app.core.errors import AppError


class ProductService:
    def __init__(self, client: EktClient):
        self.client = client

    async def search(self, query: str, *, hydrate: bool = True):
        result = await self.client.search_products(query)
        if not hydrate:
            return result
        # List responses have no quantity/properties. Enrich a bounded number of
        # matches with live details, not the whole catalog or invented stock.
        async def refresh(product):
            try:
                return await self.detail(product.id), False
            except AppError:
                return product, True
        enriched = await asyncio.gather(*[refresh(product) for product in result.products[:5]])
        result.products = [product for product, _ in enriched] + result.products[5:]
        if any(failed for _, failed in enriched) or len(result.products) > 5:
            result.partial = True
            result.message = "Каталог проверен частично; остатки и характеристики доступны не для всех результатов."
        return result

    async def detail(self, product_id: str):
        # Details, specifications and stock are always fetched live.
        return await self.client.get_product_detail(product_id)

    async def browse(self, page: int):
        result = await self.client.get_products(page)
        # EKT can repeat page one beyond its range instead of returning empty.
        if page > 1 and result.products:
            first = await self.client.get_products(1)
            if [p.id for p in result.products] == [p.id for p in first.products]:
                result.products = []
                result.has_next = False
        async def refresh(product):
            try:
                return await self.detail(product.id)
            except AppError:
                return product
        result.products = list(await asyncio.gather(*(refresh(p) for p in result.products[:5]))) + result.products[5:]
        return result
