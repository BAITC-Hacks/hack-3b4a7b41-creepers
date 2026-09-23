from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health, products, chat, cart
from app.agents.assistant import Assistant
from app.agents.tools import AssistantTools
from app.clients.ekt_client import EktClient
from app.config import Settings
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.services.product_service import ProductService
from app.services.alternative_service import AlternativeService
from app.services.session_service import SessionService
from app.services.stock_service import StockService
from app.services.cart_service import CartService
from app.schemas.chat import ChatResponse
from app.core.errors import ErrorInfo


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
        application.state.sessions = SessionService(settings)
        application.state.stock = StockService(application.state.products)
        application.state.cart = CartService(application.state.stock, settings)
        application.state.assistant = Assistant(AssistantTools(
            application.state.products, application.state.alternatives, application.state.sessions,
            application.state.cart,
        ))
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
        if request.url.path == "/api/chat":
            error = ErrorInfo(code="validation_error", message="Некорректные параметры запроса.")
            return JSONResponse(status_code=422, content=ChatResponse(message=error.message, error=error).model_dump(mode="json"))
        return JSONResponse(status_code=422, content={"error": {
            "code": "validation_error", "message": "Некорректные параметры запроса.",
        }})

    application.include_router(health.router)
    application.include_router(products.router)
    application.include_router(chat.router)
    application.include_router(cart.router)
    return application


app = create_app()
