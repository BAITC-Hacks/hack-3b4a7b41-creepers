from io import BytesIO
from zipfile import ZipFile

from app.core.errors import AppError
from app.schemas.procurement import ProcurementReport, ProcurementRow
from app.schemas.product import Product
from app.services.procurement_service import summarize
from app.services.vision_service import label_query


def chat(client, text, session="final-demo", demo=True):
    return client.post(("/demo" if demo else "") + "/api/chat", json={"session_id": session, "message": text}).json()


def test_primary_demo_natural_language_context_and_cart(client):
    session = "demo-e2e"
    search = chat(client, "Мне нужен автомат Schneider на 25А", session)
    assert [p["id"] for p in search["products"]] == ["900001"]
    assert search["products"][0]["source"] == "demo_catalog"
    assert chat(client, "Покажи характеристики", session)["products"][0]["specifications"]
    assert chat(client, "Есть сертификат?", session)["products"][0]["certificates"]
    alternatives = chat(client, "Есть ли аналог?", session)
    assert alternatives["alternatives"]
    assert "Отличия" in alternatives["alternatives"][0]["reason"]
    prepared = chat(client, "Мне нужно 5 штук", session)
    assert prepared["pending_confirmation"]["quantity"] == 5
    assert prepared["cart"]["items"] == []
    confirmed = chat(client, "Да, добавь", session)
    assert confirmed["cart"]["total_items"] == 5
    assert "mode=demo" in confirmed["checkout_url"]


def test_manufacturer_followup_and_new_rating(client):
    assert "номинальный ток" in chat(client, "Мне нужен Schneider")["message"]
    assert chat(client, "25А")["products"][0]["id"] == "900001"
    assert chat(client, "Есть ли в наличии?")["products"][0]["stock"] == "24"
    result = chat(client, "А есть на 40А?")
    assert [p["id"] for p in result["products"]] == ["900004"]


def test_kazakh_without_ai_key_and_language_switch(client):
    result = chat(client, "Маған 25А автомат керек", "kazakh")
    assert result["products"] and "Каталогтан" in result["message"]
    selected = chat(client, "900001", "kazakh")
    assert "Қолда бар" in selected["message"]
    prepared = chat(client, "5 дана қос", "kazakh")
    assert "растаңыз" in prepared["message"] and prepared["cart"]["items"] == []
    assert chat(client, "иә растаймын", "kazakh")["cart"]["total_items"] == 5
    assert "Найденные" in chat(client, "Найди автомат Schneider 25А", "kazakh")["message"]


def test_comparison_fresh_facts_and_missing_values(client, catalog):
    result = chat(client, "Сравни товары 515291 и 515292", demo=False)
    assert result["intent"] == "product_compare" and len(result["products"]) == 2
    assert result["products"][1]["price"] is None
    assert result["products"][1]["certificates"] == []
    assert "лучше" not in result["message"]
    catalog.products["515291"].stock = 1
    again = chat(client, "Сравни товары 515291 и 515292", demo=False)
    assert again["products"][0]["stock"] == "1"
    assert all(p["source"] == "ekt_catalog" for p in again["products"])


def test_stock_change_message_and_no_mutation(client, catalog):
    body = {"session_id": "stock-change"}
    assert client.post("/api/cart/prepare", json={**body, "product_id": "515291", "quantity": 10}).status_code == 200
    catalog.products["515291"].stock = 5
    result = client.post("/api/cart/confirm", json=body)
    assert result.status_code == 409 and "Сейчас доступно только 5" in result.json()["error"]["message"]
    assert client.get("/api/cart/stock-change").json()["items"] == []


def procurement_xlsx():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="urn:test"><sheetData>' + "".join(f'<row><c t="inlineStr"><is><t>{name}</t></is></c><c><v>{quantity}</v></c></row>' for name, quantity in [("Автомат Schneider 25А", 10), ("Розетка DEMO", 30), ("Кабель ВВГ", 100)]) + '</sheetData></worksheet>')
    return buffer.getvalue()


def test_excel_procurement_summary_does_not_add(client):
    result = client.post("/demo/api/chat/attachments", data={"session_id": "excel-final"}, files={"file": ("purchase.xlsx", procurement_xlsx())}).json()
    report = result["procurement"]
    assert report["positions"] == 3 and report["requested"] == 140
    assert report["available"] == 100 and report["missing"] == 40
    assert report["complete_positions"] == 2 and report["shortage_positions"] == 1
    assert client.get("/demo/api/cart/excel-final").status_code == 404
    answer = chat(client, "Проанализируй мой Excel", "excel-final")
    assert answer["intent"] == "procurement_analysis"
    assert client.get("/demo/api/cart/excel-final").json()["items"] == []
    fetched = client.get("/demo/api/chat/procurement/excel-final").json()
    assert fetched == report
    assert client.get("/api/chat/procurement/excel-final").status_code == 404


def test_procurement_duplicate_rows_cannot_overstate_stock():
    product = Product(id="a", name="Test", stock=12)
    report = summarize(ProcurementReport(rows=[ProcurementRow(query="a", requested=10, product=product), ProcurementRow(query="a", requested=10, product=product)]))
    assert report.available == 12 and report.missing == 8


def test_procurement_needs_selection_for_ambiguous_query(client):
    chat(client, "Проанализируй мой Excel", "select-row")
    bad = client.post("/demo/api/chat/procurement/select", json={"session_id": "select-row", "row_index": 0, "product_id": "515291"})
    assert bad.status_code == 422
    okay = client.post("/demo/api/chat/procurement/select", json={"session_id": "select-row", "row_index": 0, "product_id": "900001"})
    assert okay.status_code == 200 and okay.json()["rows"][0]["product"]["id"] == "900001"
    assert client.get("/demo/api/cart/select-row").json()["items"] == []


def test_photo_demo_honest_fallback_and_query_extraction(client):
    response = client.post("/demo/api/chat/attachments", data={"session_id": "photo-final"}, files={"file": ("photo.jpg", b"not actually decoded")}).json()
    assert response["analyzed"] is False and response["demo_recognition"]
    assert "демонстрационном сценарии" in response["message"]
    assert response["candidates"][0]["source"] == "demo_catalog"
    assert label_query("Автомат\nSchneider\n25A\n1P") == "Schneider 25A"
    assert label_query("Артикул: A9F74125\nSchneider") == "A9F74125"


def test_failed_catalog_and_malformed_document_are_safe(client, catalog):
    catalog.error = AppError("ekt_auth_error", "Ошибка доступа к каталогу EKT.", 502)
    result = chat(client, "Найди автомат", demo=False)
    assert result["error"]["code"] == "ekt_auth_error" and result["products"] == []
    file = client.post("/demo/api/chat/attachments", data={"session_id": "malformed"}, files={"file": ("broken.xlsx", b"PKbroken")}).json()
    assert file["analyzed"] is False and file["procurement"] is None


def test_demo_catalog_browse_pages_are_distinct_and_expanded(client):
    first = client.get("/demo/api/products?page=1").json()
    second = client.get("/demo/api/products?page=2").json()
    assert len(first["products"]) == len(second["products"]) == 12
    assert first["has_next"] is True and second["has_next"] is False
    assert not {p["id"] for p in first["products"]} & {p["id"] for p in second["products"]}
    assert all(p["source"] == "demo_catalog" for p in first["products"] + second["products"])
    assert client.get("/demo/api/products?page=3").json()["products"] == []
    assert client.get("/demo/api/products?page=0").status_code == 422
