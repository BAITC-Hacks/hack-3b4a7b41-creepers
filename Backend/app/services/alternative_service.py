import asyncio
import re

from app.core.errors import AppError
from app.schemas.product import Alternative, AlternativesResponse, Product
from app.services.product_service import ProductService


def ratings(product: Product) -> set[str]:
    text = " ".join([product.name, *product.specifications.values()]).casefold()
    return {re.sub(r"\s", "", match).replace("а", "a")
            for match in re.findall(r"\b\d+(?:[.,]\d+)?\s*[aа]\b", text)}


def specification_value(key: str, value: str) -> str:
    value = " ".join(value.casefold().split())
    if key in {"Номинальный ток", "Номинальное напряжение", "Номинальная отключающая способность"}:
        # Formatting differences in verified electrical units are not conflicts.
        return value.replace(" ", "").replace(",", ".").translate(str.maketrans({"а": "a", "к": "k", "в": "v"}))
    return value


def similarity(source: Product, candidate: Product, *, require_stock: bool = True) -> tuple[int, str] | None:
    if source.id == candidate.id or (require_stock and candidate.availability != "in_stock"):
        return None
    if source.data_warnings or candidate.data_warnings:
        return None
    if not source.category or source.category != candidate.category:
        return None
    source_ratings, candidate_ratings = ratings(source), ratings(candidate)
    if source_ratings and candidate_ratings and source_ratings != candidate_ratings:
        return None
    shared = (source.specifications.keys() & candidate.specifications.keys()) - {"Торговая марка"}
    # Conservatively exclude conflicts instead of claiming technical equivalence.
    if any(specification_value(key, source.specifications[key]) != specification_value(key, candidate.specifications[key]) for key in shared):
        return None
    equal = [key for key in shared if source.specifications[key].strip()]
    same_rating = bool(source_ratings and source_ratings == candidate_ratings)
    if not equal and not same_rating:
        return None
    score = len(equal) * 2 + int(same_rating) * 3
    reason = "Совпадает категория"
    if equal:
        reason += "; совпадают характеристики: " + ", ".join(sorted(equal)[:4])
    if same_rating:
        reason += "; совпадает указанный номинальный ток"
    reason += ". Полная взаимозаменяемость не подтверждена."
    return score, reason


class AlternativeService:
    def __init__(self, products: ProductService):
        self.products = products

    async def find(self, source: Product) -> AlternativesResponse:
        if not source.category or source.data_warnings:
            return AlternativesResponse(product=source)
        try:
            result = await self.products.search(source.category, hydrate=False)
        except AppError:
            return AlternativesResponse(product=source, partial=True)
        ranked = []
        partial = result.partial
        for candidate in result.products:
            # List items legitimately have unknown stock/specifications until
            # the detail endpoint is fetched; do not discard them prematurely.
            match = similarity(source, candidate, require_stock=False)
            if match:
                ranked.append((match[0], candidate))
        alternatives = []
        # Bounded live validation: cached search stock never proves current availability.
        async def refresh(candidate):
            try:
                return await self.products.detail(candidate.id)
            except AppError:
                return None
        refreshed = await asyncio.gather(*[
            refresh(candidate) for _, candidate in sorted(ranked, key=lambda item: (-item[0], item[1].id))[:5]
        ])
        for fresh in refreshed:
            if fresh is None:
                partial = True
                continue
            match = similarity(source, fresh)
            if match:
                alternatives.append(Alternative(product=fresh, reason=match[1]))
            if len(alternatives) == 3:
                break
        return AlternativesResponse(product=source, alternatives=alternatives, partial=partial)
