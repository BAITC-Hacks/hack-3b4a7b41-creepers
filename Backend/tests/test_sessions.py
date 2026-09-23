import asyncio
import time

import pytest

from app.config import Settings
from app.core.errors import AppError
from app.services.session_service import SessionService


async def test_expired_session_and_capacity():
    service = SessionService(Settings(_env_file=None, max_sessions=1))
    async with service.use("first"):
        pass
    with pytest.raises(AppError) as error:
        async with service.use("second"):
            pass
    assert error.value.code == "session_capacity"
    service.sessions["first"].touched_at = time.monotonic() - 3601
    async with service.use("second"):
        pass
    with pytest.raises(AppError) as error:
        async with service.use("first", create=False):
            pass
    assert error.value.code == "session_not_found"


async def test_active_session_cannot_be_evicted():
    service = SessionService(Settings(_env_file=None, max_sessions=1))
    async with service.use("first") as session:
        session.touched_at = 0
        with pytest.raises(AppError) as error:
            async with service.use("second"):
                pass
        assert error.value.code == "session_capacity"
        assert service.sessions["first"] is session
