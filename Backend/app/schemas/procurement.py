from typing import Literal
from pydantic import BaseModel, Field
from app.schemas.product import Product, Alternative


class ProcurementRow(BaseModel):
    query: str
    requested: int = Field(ge=0)
    product: Product | None = None
    candidates: list[Product] = Field(default_factory=list)
    available: int | None = None
    missing: int | None = None
    status: Literal["available", "shortage", "not_found", "selection_required", "unknown", "invalid", "error"] = "unknown"
    alternatives: list[Alternative] = Field(default_factory=list)
    note: str = ""


class ProcurementReport(BaseModel):
    rows: list[ProcurementRow] = Field(default_factory=list)
    positions: int = 0
    requested: int = 0
    available: int = 0
    missing: int = 0
    complete_positions: int = 0
    shortage_positions: int = 0
    unresolved_positions: int = 0
    truncated: bool = False
    source: Literal["ekt_catalog", "demo_catalog"] = "ekt_catalog"
    message: str = "Остатки не зарезервированы. Перед добавлением они проверяются повторно."
