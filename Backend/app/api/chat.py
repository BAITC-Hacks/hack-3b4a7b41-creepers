from fastapi import APIRouter, Request

from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    return await request.app.state.assistant.reply(body.session_id, body.message)
