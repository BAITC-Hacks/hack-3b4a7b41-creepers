"""The sole boundary for EKT transport and wire-format normalization.

Wire models verified against authenticated EKT responses on 2026-09-23.
Lists contain items/page/per_page/count; detail quantity is the stock total.
count is the returned page size, not a catalog total. Out-of-range pages can
repeat page one, so search detects repeated product IDs and remains partial.
"""
import asyncio
import re
import time
from decimal import Decimal
from html import unescape
from typing import Any, Protocol
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import Settings
from app.core.errors import AppError
from app.schemas.product import CatalogPage, Product, ProductSearchResponse


class CatalogAdapter(Protocol):
    def parse_page(self, payload: Any, page: int) -> CatalogPage: ...
    def parse_detail(self, payload: Any) -> Product: ...


class EktListItem(BaseModel):
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False, hide_input_in_errors=True)
    id: int = Field(strict=True, gt=0)
    name: str = Field(min_length=1)
    article: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    image: str | None = None
    url: str | None = None
    offers: list[Any] = Field(default_factory=list)

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, value):
        if isinstance(value, bool):
            raise ValueError("Boolean is not a price")
        return value


class EktDetail(EktListItem):
    description: str | None = None
    quantity: Decimal | None = Field(default=None, ge=0)
    # Store quantities are not added: EKT supplies its own total in quantity.
    stores: list[dict[str, Any]] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("quantity", mode="before")
    @classmethod
    def validate_quantity(cls, value):
        if isinstance(value, bool):
            raise ValueError("Boolean is not stock")
        return value


class EktPage(BaseModel):
    model_config = ConfigDict(extra="ignore", hide_input_in_errors=True)
    page: int = Field(strict=True, ge=1)
    per_page: int = Field(strict=True, ge=1)
    count: int = Field(strict=True, ge=0)
    items: list[EktListItem]

    @model_validator(mode="after")
    def validate_count(self):
        if self.count != len(self.items) or self.count > self.per_page:
            raise ValueError("Inconsistent page count")
        return self


# Only properties actually observed with this meaning are given display labels.
SPECIFICATION_LABELS = {
    "KOLICHESTVO_POLYUSOV": "Количество полюсов",
    "NOMINALNAYA_OTKLYUCHAYUSHCHAYA_SPOSOBNOST": "Номинальная отключающая способность",
    "NOMINALNOE_NAPRYAZHENIE": "Номинальное напряжение",
    "NOMINALNYY_TOK": "Номинальный ток",
    "TIP_USTANOVKI": "Тип установки",
    "TORGOVAYA_MARKA": "Торговая марка",
    "NAZNACHENIE": "Назначение",
    "TIP_USTROYSTVA": "Тип устройства",
    "KHARAKTERISTIKA_SRABATYVANIYA": "Характеристика срабатывания",
}


def _ekt_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or parsed.hostname not in {"ekt.kz", "www.ekt.kz"}
            or parsed.username or parsed.password):
        return None
    return value


def _amp_ratings(value: str) -> set[Decimal]:
    return {Decimal(match.replace(",", ".")) for match in
            re.findall(r"(?<![\w.,])([0-9]+(?:[.,][0-9]+)?)\s*[aа]\b", value.casefold())}


class EktResponseAdapter:
    """Normalize verified fields only; preserve conflicts instead of guessing."""

    def _product(self, item: EktListItem) -> Product:
        url = _ekt_url(item.url)
        category = None
        if url:
            parts = urlsplit(url).path.strip("/").split("/")
            if len(parts) >= 3 and parts[0] == "catalog":
                category = "/".join(parts[1:-1])
        specs = {}
        warnings = []
        if isinstance(item, EktDetail):
            for key, label in SPECIFICATION_LABELS.items():
                value = item.properties.get(key)
                if isinstance(value, str) and value.strip():
                    specs[label] = unescape(value.strip())
            name_ratings = _amp_ratings(item.name)
            property_ratings = _amp_ratings(specs.get("Номинальный ток", ""))
            if name_ratings and property_ratings and name_ratings != property_ratings:
                warnings.append("Номинальный ток в названии и свойствах каталога различается. Уточните характеристику у поставщика.")
        if item.offers:
            warnings.append("Товар содержит варианты исполнения. Их остатки и цены отдельно не нормализованы.")
        return Product(
            id=str(item.id), article=item.article or None, name=unescape(item.name),
            category=category, category_source="catalog_url" if category else None,
            description=unescape(item.description) if isinstance(item, EktDetail) and item.description else None,
            product_url=url, image_url=_ekt_url(item.image), specifications=specs,
            price=item.price, stock=item.quantity if isinstance(item, EktDetail) and not item.offers else None,
            # No currency or certificate fields were present in the inspected API.
            data_warnings=warnings,
        )

    def parse_page(self, payload: Any, page: int) -> CatalogPage:
        result = EktPage.model_validate(payload)
        if result.page != page:
            raise ValueError("Requested and received pages differ")
        return CatalogPage(products=[self._product(item) for item in result.items], page=page,
                           has_next=False if not result.items else None)

    def parse_detail(self, payload: Any) -> Product:
        return self._product(EktDetail.model_validate(payload))


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
    def matches(token):
        if token.startswith("автомат") and re.search(r"\b(?:ав|ва|ba)\b", product.name.casefold()):
            return True
        if token[0].isdigit():
            return re.search(r"(?<!\w)" + re.escape(token) + r"(?!\w)", haystack) is not None
        return token in haystack
    return all(matches(token) for token in search_tokens(query))


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
        seen: set[str] = set()
        # One bounded scan at a time; concurrent callers reuse cached pages.
        try:
            async with asyncio.timeout(self.settings.catalog_search_timeout_seconds):
                async with self._search_lock:
                    for page in range(1, self.settings.catalog_max_pages + 1):
                        result = await self._cached_page(page)
                        scanned += 1
                        identifiers = {product.id for product in result.products}
                        if identifiers and identifiers <= seen:
                            # EKT repeats page one for out-of-range page numbers.
                            break
                        seen.update(identifiers)
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
