from collections import Counter

import pytest
from fastapi.testclient import TestClient

from app.clients.ekt_client import matches_query
from app.config import Settings
from app.core.errors import AppError
from app.main import create_app
from app.schemas.product import Product, ProductSearchResponse


class FakeCatalog:
    """Synthetic normalized data; never mounted in the production application."""

    def __init__(self):
        self.products = {
            "515291": Product(id="515291", article="TEST-25", name="Автомат 25А",
                category="Автоматы", specifications={"Номинальный ток": "25А", "Полюса": "1"},
                certificates=["https://example.invalid/test-certificate.pdf"], stock=12, price="1500", currency="KZT"),
            "515292": Product(id="515292", article="TEST-25-B", name="Автомат 25А резерв",
                category="Автоматы", specifications={"Номинальный ток": "25А", "Полюса": "1"}, stock=8),
            "515293": Product(id="515293", name="Автомат 25А отсутствует", category="Автоматы",
                specifications={"Номинальный ток": "25А", "Полюса": "1"}, stock=0),
            "515294": Product(id="515294", name="Автомат 40А", category="Автоматы",
                specifications={"Номинальный ток": "40А", "Полюса": "1"}, stock=10),
            "515295": Product(id="515295", name="Кабель", stock=None),
        }
        self.calls = Counter()
        self.error: AppError | None = None

    async def get_product_detail(self, product_id):
        self.calls["detail"] += 1
        if self.error:
            raise self.error
        if str(product_id) not in self.products:
            raise AppError("product_not_found", "Товар не найден.", 404)
        return self.products[str(product_id)].model_copy(deep=True)

    async def search_products(self, query):
        self.calls["search"] += 1
        if self.error:
            raise self.error
        if not query.strip():
            raise AppError("invalid_query", "Введите запрос.", 422)
        return ProductSearchResponse(query=query, scanned_pages=1,
            products=[p.model_copy(deep=True) for p in self.products.values() if matches_query(p, query)])


@pytest.fixture
def catalog():
    return FakeCatalog()


@pytest.fixture
def client(catalog):
    settings = Settings(_env_file=None, ekt_api_password="")
    with TestClient(create_app(settings, ekt_client=catalog)) as client:
        yield client
