from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.errors import AppError
from app.schemas.attachment import AttachmentResponse
from app.schemas.cart import SessionId
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.attachment_service import extract_text
from app.services.vision_service import read_label

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
        if recognize_image and PurePosixPath(filename).suffix.casefold() in {".jpg", ".jpeg", ".png"} and not request.url.path.startswith("/demo/"):
            extracted = await read_label(b"".join(chunks), request.state.services.settings)
            if extracted:
                return AttachmentResponse(session_id=session_id, filename=filename, size_bytes=size, content_type=file.content_type,
                    status="text_extracted", analyzed=True, extracted_text=extracted,
                    message="AI прочитал маркировку с фото. Проверьте распознавание перед поиском: модель может ошибаться. Фото не сохранено на нашем сервере; по вашему выбору оно обработано OpenAI.")
        if extracted:
            return AttachmentResponse(session_id=session_id, filename=filename, size_bytes=size, content_type=file.content_type,
                status="text_extracted", analyzed=True, extracted_text=extracted,
                message="Извлечён текст (до 6000 символов; PDF — до 10 страниц). Выберите строку или скопируйте название в чат для поиска. Файл не сохранён; товары ещё не проверены.")
        return AttachmentResponse(session_id=session_id, filename=filename, size_bytes=size, content_type=file.content_type,
            message="Файл принят, но текст не распознан. Фото, сканы и старые XLS/DOC пока требуют ручного ввода артикула. Файл не сохранён; содержимое не использовано для подбора.")
    finally:
        await file.close()
