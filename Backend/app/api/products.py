from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.schemas.cart import ProductId
from app.schemas.product import AlternativesResponse, Product, ProductSearchResponse

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/search", response_model=ProductSearchResponse)
async def search(request: Request, q: Annotated[str, Query(min_length=1, max_length=200)]):
    return await request.state.services.products.search(q)


@router.get("/{product_id}/alternatives", response_model=AlternativesResponse)
async def alternatives(request: Request, product_id: ProductId):
    product = await request.state.services.products.detail(product_id)
    return await request.state.services.alternatives.find(product)


@router.get("/{product_id}", response_model=Product)
async def detail(request: Request, product_id: ProductId):
    return await request.state.services.products.detail(product_id)
