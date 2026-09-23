"""The sole boundary for EKT transport and wire-format normalization.

No EKT JSON fields have been verified yet: credentials were not supplied.
The adapter deliberately fails closed until real responses are inspected.
Do not replace this guard with guessed field aliases or synthetic stock.
"""
import asyncio
import re
import time
from typing import Any, Protocol

import httpx

from app.config import Settings
from app.core.errors import AppError
from app.schemas.product import CatalogPage, Product, ProductSearchResponse


class CatalogAdapter(Protocol):
    def parse_page(self, payload: Any, page: int) -> CatalogPage: ...
    def parse_detail(self, payload: Any) -> Product: ...


class EktResponseAdapter:
    """Mapping is intentionally blocked pending authenticated API inspection."""

    @staticmethod
    def _unverified():
        raise AppError(
            "ekt_schema_unverified",
            "Формат каталога EKT ещё не проверен на реальном API.", 503,
        )

    def parse_page(self, payload: Any, page: int) -> CatalogPage:
        return self._unverified()

    def parse_detail(self, payload: Any) -> Product:
        return self._unverified()


def search_tokens(value: str) -> list[str]:
    # Cyrillic А and Latin A are interchangeable only in numerical ratings.
    value = re.sub(r"(\d)\s*[аa](?=\b)", r"\1a", value.casefold())
    return re.findall(r"[\w.-]+", value, flags=re.UNICODE)


def matches_query(product: Product, query: str) -> bool:
    haystack = " ".join(search_tokens(" ".join(
        [product.id, product.article or "", product.name, product.category or ""]
        + [f"{key} {value}" for key, value in product.specifications.items()]
    )))
    # A request for 25A must not match 125A or 250A.
    return all((re.search(r"(?<!\w)" + re.escape(token) + r"(?!\w)", haystack) is not None)
               if token[0].isdigit() else token in haystack for token in search_tokens(query))


class EktClient:
    def __init__(self, settings: Settings, *, transport=None, adapter: CatalogAdapter | None = None):
        self.settings = settings
        self.adapter = adapter or EktResponseAdapter()
        self.http = httpx.AsyncClient(
            base_url=settings.ekt_api_base_url + "/",
            auth=httpx.BasicAuth(settings.ekt_api_username, settings.ekt_api_password.get_secret_value()),
            timeout=httpx.Timeout(settings.ekt_timeout_seconds),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            follow_redirects=False, transport=transport,
        )
        self._cache: dict[int, tuple[float, CatalogPage]] = {}
        self._search_lock = asyncio.Lock()

    async def close(self):
        await self.http.aclose()

    async def request_json(self, path: str, params: dict | None = None) -> Any:
        if path not in {"products", "products/detail"}:
            raise AppError("invalid_ekt_endpoint", "Недопустимый запрос каталога.")
        if not self.settings.ekt_api_username or not self.settings.ekt_api_password.get_secret_value():
            raise AppError("ekt_not_configured", "Доступ к каталогу EKT не настроен.", 503)
        try:
            response = await self.http.get(path, params=params)
        except httpx.TimeoutException:
            raise AppError("ekt_timeout", "Каталог EKT не ответил вовремя.", 504) from None
        except httpx.RequestError:
            raise AppError("ekt_unavailable", "Каталог EKT временно недоступен.", 503) from None
        if response.status_code in (401, 403):
            raise AppError("ekt_auth_error", "Ошибка доступа к каталогу EKT.", 502)
        if response.status_code == 404:
            if path == "products/detail":
                raise AppError("product_not_found", "Товар не найден.", 404)
            raise AppError("ekt_endpoint_unavailable", "Раздел каталога EKT недоступен.", 502)
        if not 200 <= response.status_code < 300:
            raise AppError("ekt_http_error", "Каталог EKT вернул ошибку.", 502)
        try:
            return response.json()
        except (ValueError, UnicodeError):
            raise AppError("ekt_invalid_json", "Каталог EKT вернул некорректные данные.", 502) from None

    async def get_products(self, page: int = 1) -> CatalogPage:
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise AppError("invalid_page", "Номер страницы должен быть положительным.")
        data = await self.request_json("products", None if page == 1 else {"page": page})
        try:
            return self.adapter.parse_page(data, page)
        except (ValueError, TypeError, KeyError):
            raise AppError("ekt_invalid_product", "Формат данных каталога EKT не поддерживается.", 502) from None

    async def get_product_detail(self, product_id: str | int) -> Product:
        if not re.fullmatch(r"[\w.-]{1,200}", str(product_id)):
            raise AppError("invalid_product_id", "Некорректный идентификатор товара.", 422)
        data = await self.request_json("products/detail", {"id": str(product_id)})
        try:
            product = self.adapter.parse_detail(data)
            if product.id != str(product_id):
                raise ValueError("Product identifier mismatch")
            return product
        except (ValueError, TypeError, KeyError):
            raise AppError("ekt_invalid_product", "Карточка товара EKT содержит некорректные данные.", 502) from None

    async def get_current_stock(self, product_id: str | int):
        return (await self.get_product_detail(product_id)).stock

    async def _cached_page(self, page: int) -> CatalogPage:
        cached = self._cache.get(page)
        if cached and time.monotonic() - cached[0] < self.settings.catalog_cache_seconds:
            return cached[1]
        result = await self.get_products(page)
        self._cache[page] = (time.monotonic(), result)
        return result

    async def search_products(self, query: str) -> ProductSearchResponse:
        query = query.strip()
        if not 1 <= len(query) <= 200 or not search_tokens(query):
            raise AppError("invalid_query", "Введите название или артикул товара.", 422)
        products: dict[str, Product] = {}
        partial = True
        scanned = 0
        # One bounded scan at a time; concurrent callers reuse cached pages.
        try:
            async with asyncio.timeout(self.settings.catalog_search_timeout_seconds):
                async with self._search_lock:
                    for page in range(1, self.settings.catalog_max_pages + 1):
                        result = await self._cached_page(page)
                        scanned += 1
                        for product in result.products:
                            if matches_query(product, query):
                                products[product.id] = product
                        if not result.products or result.has_next is False:
                            partial = False
                            break
                        if len(products) >= 20:
                            break
        except TimeoutError:
            if scanned == 0:
                raise AppError("ekt_timeout", "Поиск по каталогу EKT не завершился вовремя.", 504) from None
        found = list(products.values())[:20]
        return ProductSearchResponse(
            products=found, query=query, scanned_pages=scanned,
            partial=partial or len(products) > 20,
            message="Поиск ограничен частью каталога." if partial or len(products) > 20 else None,
        )
