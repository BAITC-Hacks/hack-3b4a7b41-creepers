import base64

import httpx
import pytest
from pydantic import ValidationError

from app.clients.ekt_client import EktClient
from app.config import Settings
from app.core.errors import AppError
from app.schemas.product import CatalogPage, Product


def settings(**kwargs):
    return Settings(_env_file=None, ekt_api_password="test-only", **kwargs)


class SyntheticAdapter:
    """Internal test transport ONLY. These fields do not describe EKT JSON."""

    def parse_page(self, payload, page):
        return CatalogPage(products=[Product.model_validate(p) for p in payload["test_items"]],
                           page=page, has_next=payload.get("test_has_next"))

    def parse_detail(self, payload):
        return Product.model_validate(payload["test_item"])


async def test_auth_endpoints_and_normalized_internal_contract():
    calls = []

    def handle(request):
        calls.append(request)
        assert request.headers["authorization"] == "Basic " + base64.b64encode(b"apiuser:test-only").decode()
        if request.url.path.endswith("/detail"):
            return httpx.Response(200, json={"test_item": {"id": "515291", "name": "Test", "stock": 0}})
        return httpx.Response(200, json={"test_items": [{"id": "515291", "name": "Test"}], "test_has_next": False})

    client = EktClient(settings(), transport=httpx.MockTransport(handle), adapter=SyntheticAdapter())
    try:
        assert (await client.get_products()).products[0].stock is None
        await client.get_products(2)
        product = await client.get_product_detail(515291)
        assert product.availability == "out_of_stock"
        assert product.price is None and product.certificates == []
        assert str(calls[0].url) == "https://ekt.kz/api/products"
        assert str(calls[1].url) == "https://ekt.kz/api/products?page=2"
        assert str(calls[2].url) == "https://ekt.kz/api/products/detail?id=515291"
    finally:
        await client.close()


@pytest.mark.parametrize("status,code", [(401, "ekt_auth_error"), (403, "ekt_auth_error"),
                                          (404, "product_not_found"), (500, "ekt_http_error"),
                                          (302, "ekt_http_error"), (429, "ekt_http_error")])
async def test_http_errors_sanitized(status, code):
    client = EktClient(settings(), transport=httpx.MockTransport(
        lambda request: httpx.Response(status, text="test-only Authorization secret")
    ))
    try:
        with pytest.raises(AppError) as error:
            await client.get_product_detail("515291")
        assert error.value.code == code
        assert "test-only" not in str(error.value)
    finally:
        await client.close()


@pytest.mark.parametrize("error_type,code", [(httpx.ReadTimeout, "ekt_timeout"), (httpx.ConnectError, "ekt_unavailable")])
async def test_network_errors_sanitized(error_type, code):
    def handle(request):
        raise error_type("test-only", request=request)
    client = EktClient(settings(), transport=httpx.MockTransport(handle))
    try:
        with pytest.raises(AppError) as error:
            await client.get_products()
        assert error.value.code == code
        assert "test-only" not in str(error.value)
    finally:
        await client.close()


async def test_malformed_json():
    client = EktClient(settings(), transport=httpx.MockTransport(lambda request: httpx.Response(200, text="<html>")))
    try:
        with pytest.raises(AppError, match="некорректные"):
            await client.get_products()
    finally:
        await client.close()


async def test_unknown_real_schema_fails_closed():
    client = EktClient(settings(), transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"id": "fake"})))
    try:
        with pytest.raises(AppError) as error:
            await client.get_products()
        assert error.value.code == "ekt_invalid_product"
    finally:
        await client.close()


async def test_missing_credentials():
    client = EktClient(Settings(_env_file=None, ekt_api_password=""))
    try:
        with pytest.raises(AppError) as error:
            await client.get_products()
        assert error.value.code == "ekt_not_configured"
    finally:
        await client.close()


@pytest.mark.parametrize("url", ["http://ekt.kz/api", "https://user:password@ekt.kz/api", "https://ekt.kz/api?token=abc"])
def test_reject_unsafe_api_url(url):
    with pytest.raises(ValidationError):
        settings(ekt_api_base_url=url)


@pytest.mark.parametrize("stock,availability", [(None, "unknown"), (0, "out_of_stock"), (12, "in_stock")])
def test_internal_stock_states(stock, availability):
    assert Product(id="1", name="Synthetic", stock=stock).availability == availability
