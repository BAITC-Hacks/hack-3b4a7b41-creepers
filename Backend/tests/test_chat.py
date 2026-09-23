import pytest

from app.agents.intent import classify
from app.core.errors import AppError


def chat(client, message, session="demo"):
    return client.post("/api/chat", json={"session_id": session, "message": message}).json()


def test_search_and_context(client, catalog):
    result = chat(client, "Мне нужен автомат на 25А")
    assert result["intent"] == "product_search" and len(result["products"]) == 3
    assert set(result) == {"message", "intent", "products", "alternatives", "pending_confirmation", "cart", "checkout_url", "error"}
    assert chat(client, "Есть в наличии?")["error"]["code"] == "product_selection_required"
    assert chat(client, "товар 515291")["products"][0]["id"] == "515291"
    catalog.products["515291"].stock = 2
    stock = chat(client, "Есть в наличии?")
    assert stock["intent"] == "stock_check" and stock["products"][0]["stock"] == "2"
    assert "Номинальный ток" in chat(client, "Покажи характеристики")["products"][0]["specifications"]
    assert chat(client, "Есть сертификат?")["products"][0]["certificates"]


def test_missing_data_and_policies(client):
    chat(client, "товар 515295")
    assert "недоступен" in chat(client, "Есть в наличии?")["message"]
    assert "не найден" in chat(client, "Есть сертификат?")["message"]
    for message, intent in [("Как оплатить?", "payment_info"), ("Есть доставка?", "delivery_info"), ("Минимальный заказ?", "minimum_order")]:
        result = chat(client, message)
        assert result["intent"] == intent and "недоступна" in result["message"]


def test_zero_stock_has_alternatives(client):
    result = chat(client, "товар 515293")
    assert result["products"][0]["availability"] == "out_of_stock"
    assert result["alternatives"]


def test_chat_upstream_error_contract(client, catalog):
    catalog.error = AppError("ekt_timeout", "Каталог не ответил.", 504)
    result = chat(client, "Найди автомат")
    assert result["error"]["code"] == "ekt_timeout" and result["products"] == []


@pytest.mark.parametrize("message", ["да", "да, добавь", "подтверждаю", "подтверждаю добавление", "yes", "Да, подтверждаю!"])
def test_explicit_confirm_classification(message):
    assert classify(message).intent == "add_to_cart_confirm"


@pytest.mark.parametrize("message", ["можно?", "а если добавить?", "добавь?", "да?", "да, но позже", "не подтверждаю", "yes?", "наверное да"])
def test_ambiguous_text_never_confirms(message):
    assert classify(message).intent != "add_to_cart_confirm"


def test_validation_and_session_isolation(client):
    result = client.post("/api/chat", json={"session_id": "demo", "message": " "})
    assert result.status_code == 422 and result.json()["error"]["code"] == "validation_error"
    chat(client, "товар 515291", "alice")
    assert chat(client, "Характеристики", "bob")["error"]["code"] == "product_selection_required"
