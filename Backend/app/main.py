from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health, products
from app.clients.ekt_client import EktClient
from app.config import Settings
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.services.product_service import ProductService
from app.services.alternative_service import AlternativeService


def create_app(settings: Settings | None = None, *, ekt_client=None) -> FastAPI:
    settings = settings or Settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        client = ekt_client or EktClient(settings)
        application.state.ekt = client
        application.state.settings = settings
        application.state.products = ProductService(client)
        application.state.alternatives = AlternativeService(application.state.products)
        try:
            yield
        finally:
            if ekt_client is None:
                await client.close()

    application = FastAPI(title="Creepers AI — EKT Assistant", version="0.1.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware, allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST"], allow_headers=["Content-Type"], allow_credentials=False,
    )

    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.info().model_dump()})

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        # Pydantic's default response echoes raw inputs; keep those out of errors.
        return JSONResponse(status_code=422, content={"error": {
            "code": "validation_error", "message": "Некорректные параметры запроса.",
        }})

    application.include_router(health.router)
    application.include_router(products.router)
    return application


app = create_app()
