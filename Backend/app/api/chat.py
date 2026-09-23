from pathlib import PurePosixPath
from typing import Annotated
import re

from fastapi import APIRouter, File, Form, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.errors import AppError
from app.schemas.attachment import AttachmentResponse
from app.schemas.cart import SessionId
from app.schemas.cart import SessionRequest, ProductId
from app.schemas.procurement import ProcurementReport
from pydantic import Field
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.attachment_service import extract_text
from app.services.vision_service import read_label, label_query

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    return await request.state.services.assistant.reply(body.session_id, body.message)


@router.post("/attachments", response_model=AttachmentResponse)
async def attachment(request: Request, session_id: Annotated[SessionId, Form()], file: Annotated[UploadFile, File()], recognize_image: Annotated[bool, Form()] = False):
    filename = PurePosixPath((file.filename or "").replace("\\", "/")).name
    try:
        if not filename or len(filename) > 255 or any(ord(char) < 32 for char in filename):
            raise AppError("invalid_filename", "Некорректное имя файла.", 422)
        if PurePosixPath(filename).suffix.casefold() not in {".xlsx", ".xls", ".docx", ".doc", ".pdf", ".jpg", ".jpeg", ".png"}:
            raise AppError("unsupported_attachment", "Формат файла не поддерживается.", 415)
        size = 0
        chunks = []
        while chunk := await file.read(65536):
            size += len(chunk)
            if size > request.state.services.settings.attachment_max_bytes:
                raise AppError("attachment_too_large", "Файл превышает допустимый размер.", 413)
            chunks.append(chunk)
        if size == 0:
            raise AppError("empty_attachment", "Файл пуст.", 422)
        extracted = await run_in_threadpool(extract_text, filename, b"".join(chunks))
        state = request.state.services
        procurement = state.assistant.tools.procurement
        is_demo = request.url.path.startswith("/demo/")
        is_image = PurePosixPath(filename).suffix.casefold() in {".jpg", ".jpeg", ".png"}
        if is_demo and is_image:
            candidates = (await state.products.search("Schneider 25А")).products
            procurement.save(session_id, photos=candidates)
            return AttachmentResponse(session_id=session_id, filename=filename, size_bytes=size, content_type=file.content_type,
                candidates=candidates, demo_recognition=True,
                message="Demo Mode: распознавание изображения работает на демонстрационном сценарии. Учебные кандидаты ниже не являются результатом анализа вашего фото.")
        if recognize_image and PurePosixPath(filename).suffix.casefold() in {".jpg", ".jpeg", ".png"} and not request.url.path.startswith("/demo/"):
            extracted = await read_label(b"".join(chunks), request.state.services.settings)
            if extracted:
                # OCR output is an untrusted search hint, never a product fact.
                hint = label_query(extracted)
                candidates = []
                try:
                    candidates = (await state.products.search(hint)).products[:5]
                except AppError:
                    pass
                procurement.save(session_id, photos=candidates)
                return AttachmentResponse(session_id=session_id, filename=filename, size_bytes=size, content_type=file.content_type,
                    status="text_extracted", analyzed=True, extracted_text=extracted,
                    candidates=candidates,
                    message="AI прочитал маркировку с фото. Проверьте распознавание перед поиском: модель может ошибаться. Фото не сохранено на нашем сервере; по вашему выбору оно обработано OpenAI.")
        if extracted:
            report = None
            if re.search(r"(?:\||\t|;)\s*\d|\b\d+\s*(?:шт|штук|дана)", extracted):
                session = state.sessions.sessions.get(session_id)
                report = await procurement.analyze(extracted, session.cart if session else None)
                procurement.save(session_id, report=report)
            return AttachmentResponse(session_id=session_id, filename=filename, size_bytes=size, content_type=file.content_type,
                status="text_extracted", analyzed=True, extracted_text=extracted,
                procurement=report,
                message="Закупка проверена по доступному каталогу. Выберите неоднозначные позиции; добавление потребует подтверждения." if report else "Извлечён текст (до 6000 символов; PDF — до 10 страниц). Выберите строку или скопируйте название в чат для поиска. Файл не сохранён; товары ещё не проверены.")
        return AttachmentResponse(session_id=session_id, filename=filename, size_bytes=size, content_type=file.content_type,
            message="Файл принят, но текст не распознан. Фото, сканы и старые XLS/DOC пока требуют ручного ввода артикула. Файл не сохранён; содержимое не использовано для подбора.")
    finally:
        await file.close()


@router.get("/procurement/{session_id}", response_model=ProcurementReport)
async def procurement_report(session_id: SessionId, request: Request):
    report = request.state.services.assistant.tools.procurement.stored(session_id)[1]
    if report is None:
        raise AppError("procurement_missing", "Сначала загрузите файл закупки или запустите демо-анализ.", 404)
    return report


class ProcurementSelection(SessionRequest):
    row_index: int = Field(ge=0, le=7)
    product_id: ProductId


@router.post("/procurement/select", response_model=ProcurementReport)
async def select_procurement(body: ProcurementSelection, request: Request):
    state = request.state.services
    service = state.assistant.tools.procurement
    report = service.stored(body.session_id)[1]
    if report is None:
        raise AppError("procurement_missing", "Сначала загрузите файл закупки.", 404)
    async with state.sessions.use(body.session_id) as session:
        updated = await service.select(report.model_copy(deep=True), body.row_index, body.product_id, session.cart)
        service.save(body.session_id, report=updated)
        session.procurement = updated
        return updated
