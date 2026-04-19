from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.vt_client import VTClient
from app.services.vmray_client import VMRayClient


async def get_session(request: Request):
    async with AsyncSession(request.app.state.db_engine) as session:
        yield session


def get_vt_client(request: Request) -> VTClient:
    return request.app.state.vt_client


def get_vmray_client(request: Request) -> VMRayClient:
    return request.app.state.vmray_client
