"""Check the actual running HTTP server without echoing secrets or inputs."""
import httpx


with httpx.Client(base_url="http://127.0.0.1:8000", trust_env=False, timeout=15) as client:
    response = client.get("/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}
    print("Health: 200 ok")
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    required = {"/health", "/api/chat", "/api/products/search", "/api/products/{product_id}",
                "/api/cart/prepare", "/api/cart/confirm", "/api/cart/cancel", "/api/cart/{session_id}"}
    assert required <= paths.keys()
    print(f"OpenAPI: 200; {len(paths)} paths; required contract present")
    response = client.get("/api/products/515291")
    result = response.json()
    print("Catalog:", response.status_code, result.get("error", {}).get("code", "product returned"))
    response = client.post("/api/chat", json={"session_id": "smoke", "message": "find 25A"})
    result = response.json()
    assert {"message", "intent", "products", "alternatives", "pending_confirmation", "cart", "checkout_url", "error"} == result.keys()
    print("Chat:", response.status_code, (result.get("error") or {}).get("code", "response returned"))
