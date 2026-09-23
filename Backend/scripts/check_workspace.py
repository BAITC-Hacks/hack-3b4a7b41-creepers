"""HTTP integration through the running Next.js proxy. No credentials required."""
from io import BytesIO
import sys
import time
from uuid import uuid4
from zipfile import ZipFile

import httpx

sys.stdout.reconfigure(encoding="utf-8")


def main():
    started = time.perf_counter()
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3000"
    with httpx.Client(base_url=base, timeout=60) as client:
        assert client.get("/backend/health").json()["status"] == "ok"
        home = client.get("/?mode=demo")
        assert home.status_code == 200 and "EKT" in home.text
        prefix = "/backend/demo/api"
        session = str(uuid4())
        body = {"session_id": session}
        assert client.get(prefix + "/status").json()["mode"] == "demo"
        detail = client.post(prefix + "/chat", json={**body, "message": "товар 900001"}).json()
        product = detail["products"][0]
        assert product["stock"] == "24" and product["certificates"]
        assert client.get("/demo-certificate.html").status_code == 200
        print("PASS page, proxy, stock, specifications, document")
        zero = client.post(prefix + "/chat", json={**body, "message": "товар 900003"}).json()
        assert zero["alternatives"] and all(a["reason"] for a in zero["alternatives"])
        assert client.post(prefix + "/cart/prepare", json={**body, "product_id": "900001", "quantity": 2}).status_code == 200
        assert client.get(prefix + "/cart/" + session).json()["items"] == []
        confirmed = client.post(prefix + "/cart/confirm", json=body).json()
        assert confirmed["total_items"] == 2
        cart_path = httpx.URL(confirmed["checkout_url"]).raw_path.decode()
        assert client.get(cart_path).status_code == 200
        assert client.get(prefix + "/cart/" + session).json()["total_items"] == 2
        assert client.get("/backend/api/cart/" + session).status_code == 404
        assert client.post(prefix + "/cart/confirm", json=body).status_code == 409
        assert client.post(prefix + "/cart/prepare", json={**body, "product_id": "900001", "quantity": 23}).status_code == 409
        assert client.post(prefix + "/cart/prepare", json={**body, "product_id": "900001", "quantity": 1}).status_code == 200
        assert client.post(prefix + "/cart/cancel", json=body).json()["cancelled"]
        assert client.post(prefix + "/cart/confirm", json=body).status_code == 409
        print("PASS alternatives, prepare/confirm, current cart URL, isolation, repeat, limits, cancel")
        for text in ("Как оплатить?", "Какая доставка?", "Минимальная партия?"):
            assert "https://ekt.kz/about/faq/" in client.post(prefix + "/chat", json={**body, "message": text}).json()["message"]
        buffer = BytesIO()
        with ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", '<w:document xmlns:w="urn:test"><w:body><w:p><w:r><w:t>Автомат 25А</w:t></w:r></w:p></w:body></w:document>')
        upload = client.post(prefix + "/chat/attachments", data=body, files={"file": ("spec.docx", buffer.getvalue())})
        assert upload.status_code == 200, upload.text
        assert "Автомат" in upload.json()["extracted_text"]
        assert client.get(prefix + "/cart/" + session).json()["total_items"] == 2
        print("PASS policy sources and multipart document extraction through proxy")
        # Final primary path: natural search -> context -> specs/certificate ->
        # alternatives -> quantity -> explicit confirmation -> actual cart link.
        primary = {"session_id": str(uuid4())}
        def say(message):
            response = client.post(prefix + "/chat", json={**primary, "message": message})
            assert response.status_code == 200
            result = response.json()
            assert not result["error"], result["message"]
            return result
        assert say("Мне нужен автомат Schneider на 25А")["products"][0]["id"] == "900001"
        assert say("Покажи характеристики")["products"][0]["specifications"]
        assert say("Есть сертификат?")["products"][0]["certificates"]
        assert say("Есть ли аналог?")["alternatives"]
        assert say("Мне нужно 5 штук")["cart"]["total_items"] == 0
        confirmed = say("Да, добавь")
        assert confirmed["cart"]["total_items"] == 5
        assert client.get(httpx.URL(confirmed["checkout_url"]).raw_path.decode()).status_code == 200
        compared = say("Сравни товары 900001 и 900002")
        assert compared["intent"] == "product_compare" and len(compared["products"]) == 2
        print("PASS primary natural-language scenario and factual comparison")
        sheet = BytesIO()
        with ZipFile(sheet, "w") as archive:
            archive.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
            archive.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
            archive.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Purchase" sheetId="1" r:id="rId1"/></sheets></workbook>')
            archive.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
            rows = [("Автомат Schneider 25А", 10), ("Розетка DEMO", 30), ("Кабель ВВГ", 100)]
            archive.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + ''.join(f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>{name}</t></is></c><c r="B{i}"><v>{quantity}</v></c></row>' for i, (name, quantity) in enumerate(rows, 1)) + '</sheetData></worksheet>')
        analyzed = client.post(prefix + "/chat/attachments", data=primary, files={"file": ("purchase.xlsx", sheet.getvalue())}).json()
        report = analyzed["procurement"]
        assert report["complete_positions"] == 2 and report["missing"] == 40
        assert client.get(prefix + "/cart/" + primary["session_id"]).json()["total_items"] == 5
        for row in report["rows"]:
            if row["available"]:
                before = client.get(prefix + "/cart/" + primary["session_id"]).json()["total_items"]
                assert client.post(prefix + "/cart/prepare", json={**primary, "product_id": row["product"]["id"], "quantity": row["available"]}).status_code == 200
                assert client.get(prefix + "/cart/" + primary["session_id"]).json()["total_items"] == before
                assert client.post(prefix + "/cart/confirm", json=primary).json()["total_items"] == before + row["available"]
        photo = client.post(prefix + "/chat/attachments", data=primary, files={"file": ("demo.jpg", b"fixture only; not a recognized image")}).json()
        assert photo["demo_recognition"] and not photo["analyzed"] and photo["candidates"]
        assert "Каталогтан" in say("Маған 25А автомат керек")["message"]
        print("PASS Excel procurement, per-item confirmation, honest photo demo, RU/KZ")
        status = client.get("/backend/api/status").json()
        if status["catalog_configured"]:
            live_started = time.perf_counter()
            response = client.get("/backend/api/products/515282")
            assert response.status_code == 200, "Live EKT API unavailable"
            assert response.json()["id"] == "515282"
            print(f"PASS live EKT product via proxy ({time.perf_counter() - live_started:.2f}s)")
        else:
            print("SKIP live EKT: credentials not configured; offline demo passed")
    print(f"Workspace HTTP checks passed ({time.perf_counter() - started:.2f}s). Browser interaction was not tested.")


if __name__ == "__main__":
    main()
