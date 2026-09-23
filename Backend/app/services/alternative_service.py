import asyncio
import re

from app.core.errors import AppError
from app.schemas.product import Alternative, AlternativesResponse, Product
from app.services.product_service import ProductService


def ratings(product: Product) -> set[str]:
    text = " ".join([product.name, *product.specifications.values()]).casefold()
    return {re.sub(r"\s", "", match).replace("а", "a")
            for match in re.findall(r"\b\d+(?:[.,]\d+)?\s*[aа]\b", text)}


def similarity(source: Product, candidate: Product) -> tuple[int, str] | None:
    if source.id == candidate.id or candidate.availability != "in_stock":
        return None
    if not source.category or source.category != candidate.category:
        return None
    source_ratings, candidate_ratings = ratings(source), ratings(candidate)
    if source_ratings and candidate_ratings and source_ratings != candidate_ratings:
        return None
    shared = source.specifications.keys() & candidate.specifications.keys()
    # Conservatively exclude conflicts instead of claiming technical equivalence.
    if any(source.specifications[key].casefold() != candidate.specifications[key].casefold() for key in shared):
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
        if not source.category:
            return AlternativesResponse(product=source)
        try:
            result = await self.products.search(source.category)
        except AppError:
            return AlternativesResponse(product=source, partial=True)
        ranked = []
        partial = result.partial
        for candidate in result.products:
            match = similarity(source, candidate)
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
