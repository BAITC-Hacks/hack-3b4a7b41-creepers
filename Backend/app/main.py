from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health, products, chat, cart
from app.agents.assistant import Assistant
from app.agents.tools import AssistantTools
from app.agents.language import LanguageRouter
from app.clients.demo_catalog import DemoCatalog
from app.services.conditions_service import POLICIES, SOURCE
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
        ), LanguageRouter(settings))
        demo_products = ProductService(DemoCatalog(settings.demo_checkout_base_url))
        demo = SimpleNamespace(settings=settings, products=demo_products,
            alternatives=AlternativeService(demo_products), sessions=SessionService(settings))
        demo.cart = CartService(StockService(demo_products), settings, demo=True)
        demo.assistant = Assistant(AssistantTools(demo.products, demo.alternatives, demo.sessions, demo.cart))
        application.state.demo = demo
        try:
            yield
        finally:
            if ekt_client is None:
                await client.close()

    application = FastAPI(title="Creepers AI — EKT Assistant", version="0.1.0", lifespan=lifespan)
    @application.middleware("http")
    async def upload_size_guard(request: Request, call_next):
        request.state.services = request.app.state.demo if request.url.path.startswith("/demo/") else request.app.state
        if request.url.path.endswith("/api/chat/attachments") and request.method == "POST":
            length = request.headers.get("content-length", "")
            if not length.isascii() or not length.isdigit() or request.headers.get("transfer-encoding"):
                return JSONResponse(status_code=411, content={"error": {"code": "content_length_required", "message": "Для загрузки требуется Content-Length."}})
            if len(length) > 12 or int(length) > settings.attachment_max_bytes + 65536:
                return JSONResponse(status_code=413, content={"error": {"code": "attachment_too_large", "message": "Файл превышает допустимый размер."}})
        return await call_next(request)

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
    for router in (health.router, products.router, chat.router, cart.router):
        application.include_router(router, prefix="/demo")

    @application.get("/api/status")
    @application.get("/demo/api/status")
    async def status(request: Request):
        is_demo = request.url.path.startswith("/demo/")
        return {"mode": "demo" if is_demo else "live", "catalog_configured": is_demo or bool(settings.ekt_api_password.get_secret_value()),
                "language_model_configured": not is_demo and bool(settings.openai_api_key.get_secret_value()),
                "policies": POLICIES, "policy_source": SOURCE, "policy_checked_at": "2026-09-23"}
    return application


app = create_app()
