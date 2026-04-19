from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, get_vt_client, get_vmray_client
from app.services.pipeline import (
    URLProcessPipeline,
    VMRayPollPipeline,
    VMRaySubmitPipeline,
    VTPipeline,
)
from app.services.vt_client import VTClient
from app.services.vmray_client import VMRayClient

router = APIRouter(prefix="/internal")


@router.post("/vt/poll")
async def vt_poll(
    session: AsyncSession = Depends(get_session),
    vt_client: VTClient = Depends(get_vt_client),
):
    vt_result = await VTPipeline(session, vt_client).run()
    url_result = await URLProcessPipeline(session).run()
    return {"vt": vt_result, "urls": url_result}


@router.post("/urls/extract")
async def urls_extract(session: AsyncSession = Depends(get_session)):
    return await URLProcessPipeline(session).run()


@router.post("/vmray/submit")
async def vmray_submit(
    session: AsyncSession = Depends(get_session),
    vmray_client: VMRayClient = Depends(get_vmray_client),
):
    return await VMRaySubmitPipeline(session, vmray_client).run()


@router.post("/vmray/poll")
async def vmray_poll(
    session: AsyncSession = Depends(get_session),
    vmray_client: VMRayClient = Depends(get_vmray_client),
):
    return await VMRayPollPipeline(session, vmray_client).run()
