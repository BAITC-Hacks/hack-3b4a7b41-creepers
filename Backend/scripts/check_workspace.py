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
