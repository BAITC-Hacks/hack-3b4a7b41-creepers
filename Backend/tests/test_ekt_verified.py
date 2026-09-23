"""Regression tests against catalog responses inspected on 2026-09-23.

These snapshots prove the wire mapping, not current prices or availability.
Authentication headers/credentials are not part of these fixtures.
"""
import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.clients.ekt_client import EktClient, EktResponseAdapter, matches_query
from app.main import create_app
from app.services.alternative_service import similarity
from tests.test_ekt_client import settings


@pytest.fixture
def verified():
    return json.loads((Path(__file__).parent / "fixtures/ekt_verified.json").read_text(encoding="utf-8"))


def test_actual_page_fields_and_count_is_not_total(verified):
    page = EktResponseAdapter().parse_page(verified["page2"], 2)
    assert len(page.products) == 20 and page.page == 2
    assert page.has_next is None  # count=20 does not mean only 20 products exist.
    assert page.products[0].id == "515291"
    assert page.products[0].article == "200300285_"
    assert page.products[0].stock is None and page.products[0].availability == "unknown"
    assert page.products[0].specifications == {}


def test_actual_detail_quantity_properties_and_no_fabricated_fields(verified):
    product = EktResponseAdapter().parse_detail(verified["detail25"])
    assert product.id == "515282" and product.article == "200300276_"
    assert product.stock == 34 and product.price == Decimal("29810")
    assert product.availability == "in_stock"
    assert product.specifications["Количество полюсов"] == "3"
    assert product.specifications["Номинальный ток"] == "25 А"
    assert product.currency is None and product.certificates == []
    assert product.category_source == "catalog_url"
    assert product.category.endswith("/drx125_mt_10_250_a_legrand")
    assert product.data_warnings == []
    assert "RECOMMEND" not in product.specifications
    assert matches_query(product, "автомат 25A")


def test_api_conflicting_rating_is_preserved_and_flagged(verified):
    product = EktResponseAdapter().parse_detail(verified["detail"])
    assert "160А" in product.name
    assert product.specifications["Номинальный ток"] == "250 А"
    assert product.data_warnings
    candidate = product.model_copy(update={"id": "another"})
    assert similarity(product, candidate) is None


def test_unknown_stock_never_summed_from_stores(verified):
    payload = deepcopy(verified["detail25"])
    del payload["quantity"]
    product = EktResponseAdapter().parse_detail(payload)
    assert product.stock is None and product.availability == "unknown"


def test_uninspected_variants_do_not_supply_orderable_stock(verified):
    payload = deepcopy(verified["detail25"])
    payload["offers"] = [{"unverified": "variant shape"}]
    product = EktResponseAdapter().parse_detail(payload)
    assert product.stock is None and product.data_warnings


@pytest.mark.parametrize("field,value", [("quantity", -1), ("quantity", True), ("quantity", "NaN"), ("price", False), ("id", True)])
def test_invalid_wire_values_rejected(verified, field, value):
    payload = deepcopy(verified["detail25"])
    payload[field] = value
    with pytest.raises(ValidationError):
        EktResponseAdapter().parse_detail(payload)


def test_wrong_page_or_count_rejected(verified):
    adapter = EktResponseAdapter()
    with pytest.raises(ValueError):
        adapter.parse_page(verified["page1"], 2)
    payload = deepcopy(verified["page1"])
    payload["count"] = 10000
    with pytest.raises(ValueError):
        adapter.parse_page(payload, 1)


async def test_actual_pagination_wrap_is_bounded_and_partial(verified):
    calls = []
    def handle(request):
        page = int(request.url.params.get("page", 1))
        calls.append(page)
        payload = deepcopy(verified["page1"])
        payload["page"] = page  # Observed EKT behavior beyond catalog end.
        return httpx.Response(200, json=payload)
    client = EktClient(settings(catalog_max_pages=10), transport=httpx.MockTransport(handle))
    try:
        result = await client.search_products("25A")
        assert calls == [1, 2] and result.partial
        assert [product.id for product in result.products] == ["515282"]
    finally:
        await client.close()


def test_actual_responses_drive_chat_and_confirm_flow(verified):
    def handle(request):
        if request.url.path.endswith("/detail"):
            identifier = request.url.params["id"]
            for name in ["detail25", "detail", "other25"]:
                if str(verified[name]["id"]) == identifier:
                    return httpx.Response(200, json=verified[name])
            return httpx.Response(404)
        page = int(request.url.params.get("page", 1))
        if page <= 2:
            return httpx.Response(200, json=verified[f"page{page}"])
        return httpx.Response(200, json={"page": page, "per_page": 20, "count": 0, "items": []})
    ekt = EktClient(settings(), transport=httpx.MockTransport(handle))
    with TestClient(create_app(settings(), ekt_client=ekt)) as client:
        def chat(message):
            response = client.post("/api/chat", json={"session_id": "verified", "message": message})
            assert response.status_code == 200
            assert response.json()["error"] is None
            return response.json()
        result = chat("Мне нужен автомат на 25А")
        assert [p["id"] for p in result["products"]] == ["515282"]
        assert result["products"][0]["stock"] == "34"
        assert chat("Есть в наличии?")["products"][0]["availability"] == "in_stock"
        assert chat("Покажи характеристики")["products"][0]["specifications"]["Номинальный ток"] == "25 А"
        assert "не найден" in chat("Есть сертификат?")["message"]
        assert chat("Добавь 5 штук")["pending_confirmation"]["quantity"] == 5
        assert client.get("/api/cart/verified").json()["total_items"] == 0
        assert chat("Да, подтверждаю")["cart"]["total_items"] == 5


def test_actual_zero_stock(verified):
    product = EktResponseAdapter().parse_detail(verified["other25"])
    assert product.stock == 0 and product.availability == "out_of_stock"
    assert product.certificates == []
