from app.clients.ekt_client import EktClient


class ProductService:
    def __init__(self, client: EktClient):
        self.client = client

    async def search(self, query: str):
        return await self.client.search_products(query)

    async def detail(self, product_id: str):
        # Details, specifications and stock are always fetched live.
        return await self.client.get_product_detail(product_id)
