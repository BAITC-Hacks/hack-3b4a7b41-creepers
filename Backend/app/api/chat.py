from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile

from app.core.errors import AppError
from app.schemas.attachment import AttachmentResponse
from app.schemas.cart import SessionId
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    return await request.app.state.assistant.reply(body.session_id, body.message)


@router.post("/attachments", response_model=AttachmentResponse)
async def attachment(request: Request, session_id: Annotated[SessionId, Form()], file: Annotated[UploadFile, File()]):
    filename = PurePosixPath((file.filename or "").replace("\\", "/")).name
    try:
        if not filename or len(filename) > 255 or any(ord(char) < 32 for char in filename):
            raise AppError("invalid_filename", "Некорректное имя файла.", 422)
        if PurePosixPath(filename).suffix.casefold() not in {".xlsx", ".xls", ".docx", ".doc", ".pdf", ".jpg", ".jpeg", ".png"}:
            raise AppError("unsupported_attachment", "Формат файла не поддерживается.", 415)
        size = 0
        while chunk := await file.read(65536):
            size += len(chunk)
            if size > request.app.state.settings.attachment_max_bytes:
                raise AppError("attachment_too_large", "Файл превышает допустимый размер.", 413)
        if size == 0:
            raise AppError("empty_attachment", "Файл пуст.", 422)
        return AttachmentResponse(session_id=session_id, filename=filename, size_bytes=size, content_type=file.content_type)
    finally:
        await file.close()
