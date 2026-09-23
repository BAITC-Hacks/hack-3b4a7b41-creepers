from fastapi import APIRouter, Request

from app.schemas.cart import (
    CancelResponse, CartPrepareRequest, CartResponse,
    PendingConfirmation, SessionId, SessionRequest,
)

router = APIRouter(prefix="/api/cart", tags=["cart"])


@router.post("/prepare", response_model=PendingConfirmation)
async def prepare(body: CartPrepareRequest, request: Request):
    state = request.state.services
    async with state.sessions.use(body.session_id) as session:
        pending = await state.cart.prepare(session, body.product_id, body.quantity)
        state.sessions.remember(session, [pending.product])
        return pending


@router.post("/confirm", response_model=CartResponse)
async def confirm(body: SessionRequest, request: Request):
    state = request.state.services
    async with state.sessions.use(body.session_id, create=False) as session:
        return await state.cart.confirm(session)


@router.post("/cancel", response_model=CancelResponse)
async def cancel(body: SessionRequest, request: Request):
    state = request.state.services
    async with state.sessions.use(body.session_id, create=False) as session:
        cancelled = state.cart.cancel(session)
        return CancelResponse(cancelled=cancelled, cart=state.cart.view(session))


@router.get("/{session_id}", response_model=CartResponse)
async def get_cart(session_id: SessionId, request: Request):
    state = request.state.services
    async with state.sessions.use(session_id, create=False) as session:
        return state.cart.view(session)
