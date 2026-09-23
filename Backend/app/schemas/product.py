from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class Product(BaseModel):
    """Normalized catalog data; unavailable values are never manufactured."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_assignment=True)
    id: str = Field(min_length=1, max_length=200)
    article: str | None = None
    name: str = Field(min_length=1)
    category: str | None = None
    category_source: Literal["catalog_url"] | None = None
    description: str | None = None
    product_url: str | None = None
    image_url: str | None = None
    specifications: dict[str, str] = Field(default_factory=dict)
    certificates: list[str] = Field(default_factory=list)
    price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = None
    stock: Decimal | None = Field(default=None, ge=0)
    data_warnings: list[str] = Field(default_factory=list)

    @computed_field
    @property
    def availability(self) -> Literal["in_stock", "out_of_stock", "unknown"]:
        if self.stock is None:
            return "unknown"
        return "in_stock" if self.stock > 0 else "out_of_stock"


class CatalogPage(BaseModel):
    products: list[Product]
    page: int = Field(ge=1)
    has_next: bool | None = None


class ProductSearchResponse(BaseModel):
    products: list[Product] = Field(default_factory=list)
    query: str
    scanned_pages: int = 0
    partial: bool = False
    message: str | None = None


class Alternative(BaseModel):
    product: Product
    reason: str


class AlternativesResponse(BaseModel):
    product: Product
    alternatives: list[Alternative] = Field(default_factory=list)
    partial: bool = False
