from typing import Literal

from pydantic import BaseModel

from app.schemas.cart import SessionId
from app.schemas.procurement import ProcurementReport
from app.schemas.product import Product
from pydantic import Field


class AttachmentResponse(BaseModel):
    session_id: SessionId
    filename: str
    size_bytes: int
    content_type: str | None
    status: Literal["metadata_only", "text_extracted"] = "metadata_only"
    analyzed: bool = False
    extracted_text: str | None = None
    procurement: ProcurementReport | None = None
    candidates: list[Product] = Field(default_factory=list)
    demo_recognition: bool = False
    message: str = "Получены только метаданные файла. Содержимое не анализировалось и не сохранено."
