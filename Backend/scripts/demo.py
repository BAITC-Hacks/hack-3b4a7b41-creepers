"""Run the requested workflow against a server or an explicitly synthetic app."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import uuid4

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def workflow(client):
    session = "demo-" + uuid4().hex
    async def chat(message):
        response = await client.post("/api/chat", json={"session_id": session, "message": message})
        response.raise_for_status()
        result = response.json()
        if result["error"]:
            print(json.dumps({"error": result["error"]["code"]}))
            raise RuntimeError("Demo cannot continue; configure and validate the real EKT adapter first.")
        print(json.dumps({"intent": result["intent"], "products": len(result["products"]),
                          "pending": result["pending_confirmation"] is not None,
                          "cart_items": result["cart"]["total_items"] if result["cart"] else 0}))
        return result

    result = await chat("Мне нужен автомат на 25А")
    available = [p for p in result["products"] if p["stock"] is not None and float(p["stock"]) >= 5]
    if not available:
        raise RuntimeError("Demo needs a verified product with at least 5 units in the scanned catalog.")
    await chat("товар " + available[0]["id"])
    await chat("Есть в наличии?")
    await chat("Покажи характеристики")
    await chat("Есть сертификат?")
    pending = await chat("Добавь 5 штук")
    assert pending["pending_confirmation"] and pending["cart"]["total_items"] == 0
    assert (await client.get(f"/api/cart/{session}")).json()["total_items"] == 0
    result = await chat("Да, подтверждаю")
    assert result["cart"]["total_items"] == 5 and result["checkout_url"]
    print("PASS: prepare did not mutate; explicit confirmation added 5; demo checkout URL returned.")
    # A separate catalog request finds the optional zero-stock scenario.
    search = (await client.get("/api/products/search", params={"q": "25A"})).json()
    zero = [p for p in search.get("products", []) if p["availability"] == "out_of_stock"]
    if zero:
        detail = await chat("товар " + zero[0]["id"])
        print(json.dumps({"zero_stock_demo": True, "alternatives": len(detail["alternatives"])}))


async def main(args):
    if args.synthetic:
        from app.config import Settings
        from app.main import create_app
        from tests.conftest import FakeCatalog
        print("SYNTHETIC TEST DATA ONLY. This does not validate EKT API integration.")
        app = create_app(Settings(_env_file=None, ekt_api_password=""), ekt_client=FakeCatalog())
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://demo") as client:
                await workflow(client)
    else:
        async with httpx.AsyncClient(base_url=args.base_url, timeout=30, trust_env=False) as client:
            await workflow(client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic", action="store_true", help="Run isolated ASGI demo with test fixtures, never real data")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    try:
        asyncio.run(main(args))
    except (RuntimeError, httpx.HTTPError) as exc:
        print("Demo did not complete. Check server configuration and availability.")
        raise SystemExit(1) from None
