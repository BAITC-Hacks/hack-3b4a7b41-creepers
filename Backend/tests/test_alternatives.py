from app.services.alternative_service import similarity


def test_zero_stock_alternative(client):
    response = client.get("/api/products/515293/alternatives")
    assert response.status_code == 200
    alternatives = response.json()["alternatives"]
    assert {item["product"]["id"] for item in alternatives} == {"515291", "515292"}
    assert all("не подтверждена" in item["reason"] for item in alternatives)


def test_reject_different_rating_category_and_unknown_stock(catalog):
    source = catalog.products["515293"]
    assert similarity(source, catalog.products["515294"]) is None
    assert similarity(source, catalog.products["515295"]) is None
    candidate = catalog.products["515291"].model_copy(update={"category": "Другая категория"})
    assert similarity(source, candidate) is None


def test_fresh_availability_rechecked(client, catalog):
    original = catalog.get_product_detail
    async def changed(product_id):
        product = await original(product_id)
        if product_id in {"515291", "515292"}:
            product.stock = 0
        return product
    catalog.get_product_detail = changed
    assert client.get("/api/products/515293/alternatives").json()["alternatives"] == []


def test_no_alternative_without_comparable_data(client):
    assert client.get("/api/products/515295/alternatives").json()["alternatives"] == []


def test_search_failure_preserves_known_product(client, catalog):
    from app.core.errors import AppError
    async def unavailable(query):
        raise AppError("ekt_unavailable", "Каталог недоступен.", 503)
    catalog.search_products = unavailable
    response = client.get("/api/products/515293/alternatives")
    assert response.status_code == 200
    assert response.json()["product"]["availability"] == "out_of_stock"
    assert response.json()["partial"] is True and response.json()["alternatives"] == []
