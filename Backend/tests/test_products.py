import httpx
import pytest

from app.clients.ekt_client import EktClient
from app.clients.ekt_client import matches_query
from app.schemas.product import Product
from tests.test_ekt_client import SyntheticAdapter, settings


def test_rating_does_not_match_larger_number():
    assert matches_query(Product(id="1", name="Автомат 25А"), "25A")
    assert not matches_query(Product(id="2", name="Автомат 125А"), "25A")
    assert not matches_query(Product(id="3", name="Автомат 250А"), "25A")


async def test_total_search_deadline():
    import asyncio
    from app.core.errors import AppError
    async def slow(request):
        await asyncio.sleep(0.1)
        return httpx.Response(200, json={"test_items": []})
    client = EktClient(settings(catalog_search_timeout_seconds=0.01), transport=httpx.MockTransport(slow), adapter=SyntheticAdapter())
    try:
        with pytest.raises(AppError) as error:
            await client.search_products("25A")
        assert error.value.code == "ekt_timeout"
    finally:
        await client.close()


def test_search_and_detail(client):
    response = client.get("/api/products/search", params={"q": "25A"})
    assert response.status_code == 200
    assert len(response.json()["products"]) == 3
    detail = client.get("/api/products/515291").json()
    assert detail["article"] == "TEST-25"
    assert detail["specifications"]["Номинальный ток"] == "25А"
    assert detail["certificates"] and detail["availability"] == "in_stock"


def test_empty_and_invalid_search(client):
    assert client.get("/api/products/search", params={"q": "xyzabc"}).json()["products"] == []
    for query in ["", "   ", "x" * 201]:
        assert client.get("/api/products/search", params={"q": query}).status_code == 422


def test_zero_unknown_and_missing_product(client):
    assert client.get("/api/products/515293").json()["availability"] == "out_of_stock"
    assert client.get("/api/products/515295").json()["availability"] == "unknown"
    assert client.get("/api/products/missing").status_code == 404


async def test_bounded_pagination_cache_and_fresh_stock():
    calls = []
    stock = 10
    def handle(request):
        calls.append(request)
        product = {"id": "1", "name": "Автомат 25А", "stock": stock}
        if request.url.path.endswith("/detail"):
            return httpx.Response(200, json={"test_item": product})
        return httpx.Response(200, json={"test_items": [product], "test_has_next": True})
    client = EktClient(settings(catalog_max_pages=2), transport=httpx.MockTransport(handle), adapter=SyntheticAdapter())
    try:
        result = await client.search_products("25A")
        assert len(result.products) == 1 and result.partial and result.scanned_pages == 2
        await client.search_products("25А")
        assert len(calls) == 2
        stock = 0
        assert await client.get_current_stock("1") == 0
        assert len(calls) == 3
    finally:
        await client.close()


async def test_pagination_ends_on_confirmed_last_page():
    client = EktClient(settings(), transport=httpx.MockTransport(lambda request: httpx.Response(200, json={
        "test_items": [], "test_has_next": False,
    })), adapter=SyntheticAdapter())
    try:
        result = await client.search_products("none")
        assert result.scanned_pages == 1 and not result.partial
    finally:
        await client.close()


@pytest.mark.parametrize("payload", [{"test_item": {"name": "No ID"}}, {"test_item": {"id": "wrong", "name": "Bad"}}, {"test_item": {"id": "1", "name": "Bad", "stock": -1}}])
async def test_reject_invalid_upstream_product(payload):
    from app.core.errors import AppError
    client = EktClient(settings(), transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload)), adapter=SyntheticAdapter())
    try:
        with pytest.raises(AppError) as error:
            await client.get_product_detail("1")
        assert error.value.code == "ekt_invalid_product"
    finally:
        await client.close()
