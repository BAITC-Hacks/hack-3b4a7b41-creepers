import asyncio
import time

import httpx
import pytest

from app.config import Settings
from app.main import create_app
from tests.test_chat import chat


def prepare(client, quantity=5, product="515291", session="demo"):
    return client.post("/api/cart/prepare", json={"session_id": session, "product_id": product, "quantity": quantity})


def confirm(client, session="demo"):
    return client.post("/api/cart/confirm", json={"session_id": session})


def test_prepare_does_not_mutate_confirm_returns_demo_url(client, catalog):
    result = prepare(client)
    assert result.status_code == 200 and result.json()["pending_confirmation"] is True
    assert result.json()["available_stock"] == "12"
    assert client.get("/api/cart/demo").json()["total_items"] == 0
    before = catalog.calls["detail"]
    response = confirm(client)
    assert response.status_code == 200
    assert catalog.calls["detail"] == before + 1
    assert response.json()["total_items"] == 5
    assert response.json()["checkout_url"] == "http://localhost:3000/cart/demo"
    assert confirm(client).status_code == 409
    assert client.get("/api/cart/demo").json()["total_items"] == 5


@pytest.mark.parametrize("quantity", [0, -1, 1.5, True, "5", 1000001])
def test_invalid_quantity(client, quantity):
    assert prepare(client, quantity=quantity).status_code == 422


def test_insufficient_or_unknown_stock(client):
    assert prepare(client, quantity=13).json()["error"]["code"] == "insufficient_stock"
    assert prepare(client, product="515293").json()["error"]["code"] == "insufficient_stock"
    assert prepare(client, product="515295").json()["error"]["code"] == "stock_unknown"
    assert client.get("/api/cart/demo").json()["total_items"] == 0


@pytest.mark.parametrize("stock", [3, 0, None])
def test_stock_changed_before_confirmation(client, catalog, stock):
    prepare(client)
    catalog.products["515291"].stock = stock
    assert confirm(client).status_code == 409
    assert client.get("/api/cart/demo").json()["items"] == []
    assert confirm(client).json()["error"]["code"] == "pending_action_missing"


def test_existing_cart_quantity_counts_against_stock(client, catalog):
    prepare(client, quantity=8)
    confirm(client)
    assert prepare(client, quantity=5).status_code == 409
    assert prepare(client, quantity=4).status_code == 200
    catalog.products["515291"].stock = 10
    assert confirm(client).status_code == 409
    assert client.get("/api/cart/demo").json()["total_items"] == 8


def test_cancel_preserves_cart(client):
    prepare(client, quantity=2)
    confirm(client)
    prepare(client, quantity=3)
    cancelled = client.post("/api/cart/cancel", json={"session_id": "demo"})
    assert cancelled.status_code == 200 and cancelled.json()["cancelled"]
    assert cancelled.json()["cart"]["total_items"] == 2
    assert confirm(client).status_code == 409


def test_no_action_missing_session_and_session_isolation(client):
    assert confirm(client, "missing").status_code == 404
    assert client.get("/api/cart/missing").status_code == 404
    prepare(client, session="alice")
    chat(client, "привет", "bob")
    assert confirm(client, "bob").status_code == 409
    assert confirm(client, "alice").json()["total_items"] == 5
    assert client.get("/api/cart/bob").json()["items"] == []


def test_expired_action(client):
    prepare(client)
    client.app.state.sessions.sessions["demo"].pending_cart_action.created_at = time.monotonic() - 301
    assert confirm(client).json()["error"]["code"] == "pending_action_expired"
    assert client.get("/api/cart/demo").json()["items"] == []


def test_cart_through_chat(client):
    chat(client, "товар 515291")
    pending = chat(client, "Добавь 5 штук")
    assert pending["intent"] == "add_to_cart_prepare" and pending["pending_confirmation"]["quantity"] == 5
    assert pending["cart"]["total_items"] == 0
    for ambiguous in ["можно?", "а если добавить?", "добавь?", "да?"]:
        chat(client, ambiguous)
        assert client.get("/api/cart/demo").json()["total_items"] == 0
    result = chat(client, "Да, подтверждаю")
    assert result["intent"] == "add_to_cart_confirm" and result["cart"]["total_items"] == 5
    assert result["checkout_url"].endswith("/cart/demo")


def test_chat_cancel_and_product_switch_invalidate_pending(client):
    chat(client, "товар 515291")
    chat(client, "добавь 5 штук")
    chat(client, "отмена")
    assert chat(client, "да")["error"]["code"] == "pending_action_missing"
    chat(client, "добавь 5 штук")
    chat(client, "товар 515292")
    assert chat(client, "да")["error"]["code"] == "pending_action_missing"


@pytest.mark.parametrize("message", ["добавь -1 штук", "добавь 0 штук", "добавь 1.5 штук"])
def test_chat_invalid_quantities(client, message):
    chat(client, "товар 515291")
    assert chat(client, message)["error"]["code"] == "invalid_quantity"
    assert client.get("/api/cart/demo").json()["items"] == []


async def test_concurrent_confirmation_only_adds_once(catalog):
    original = catalog.get_product_detail
    async def slow_detail(product_id):
        await asyncio.sleep(0.01)
        return await original(product_id)
    catalog.get_product_detail = slow_detail
    app = create_app(Settings(_env_file=None), ekt_client=catalog)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/cart/prepare", json={"session_id": "demo", "product_id": "515291", "quantity": 5})
            responses = await asyncio.gather(*[
                client.post("/api/cart/confirm", json={"session_id": "demo"}) for _ in range(2)
            ])
            assert sorted(response.status_code for response in responses) == [200, 409]
            assert (await client.get("/api/cart/demo")).json()["total_items"] == 5
