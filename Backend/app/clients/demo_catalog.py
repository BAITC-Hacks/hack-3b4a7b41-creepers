"""Explicit offline demonstration data. Never a fallback for EKT failures."""
from app.clients.ekt_client import matches_query
from app.core.errors import AppError
from app.schemas.product import Product, ProductSearchResponse


class DemoCatalog:
    def __init__(self, checkout_base: str):
        specs = {"Номинальный ток": "25А", "Количество полюсов": "1", "Номинальное напряжение": "230В", "Характеристика срабатывания": "C"}
        self.products = {
            "900001": Product(id="900001", article="DEMO-C25", name="Автоматический выключатель C25 · 1P", category="Автоматы", description="Учебная позиция для проверки подбора и корзины. Данные синтетические.", specifications=specs, stock=24, price="2450", currency="KZT", certificates=[f"{checkout_base}/demo-certificate.html"]),
            "900002": Product(id="900002", article="DEMO-C25-ALT", name="Автоматический выключатель C25 · аналог", category="Автоматы", specifications=specs, stock=18, price="2690", currency="KZT"),
            "900003": Product(id="900003", article="DEMO-C25-ZERO", name="Автоматический выключатель C25 · нет в наличии", category="Автоматы", specifications=specs, stock=0, price="2300", currency="KZT"),
            "900004": Product(id="900004", article="DEMO-C40", name="Автоматический выключатель C40 · 1P", category="Автоматы", specifications={**specs, "Номинальный ток": "40А"}, stock=12, price="3100", currency="KZT"),
            "900005": Product(id="900005", article="DEMO-CABLE", name="Кабель ВВГнг 3×2,5", category="Кабель", specifications={"Количество жил": "3", "Сечение": "2,5 мм²"}, stock=120, price="780", currency="KZT", description="Учебная единица продажи: 1 метр."),
        }

    async def get_product_detail(self, product_id):
        product = self.products.get(str(product_id))
        if product is None:
            raise AppError("product_not_found", "Товар не найден в учебном каталоге.", 404)
        return product.model_copy(deep=True)

    async def search_products(self, query):
        return ProductSearchResponse(query=query, scanned_pages=1, products=[p.model_copy(deep=True) for p in self.products.values() if matches_query(p, query)])
