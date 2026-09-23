from typing import Literal

from pydantic import BaseModel

from app.schemas.cart import SessionId


class AttachmentResponse(BaseModel):
    session_id: SessionId
    filename: str
    size_bytes: int
    content_type: str | None
    status: Literal["metadata_only", "text_extracted"] = "metadata_only"
    analyzed: bool = False
    extracted_text: str | None = None
    message: str = "Получены только метаданные файла. Содержимое не анализировалось и не сохранено."
