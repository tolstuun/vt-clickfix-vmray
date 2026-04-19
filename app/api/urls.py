import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.models.url import URL
from app.models.vmray_submission import VMRaySubmission
from app.schemas.url import URLListResponse, URLOut, VMRaySubmissionOut

router = APIRouter(prefix="/urls")


@router.get("", response_model=URLListResponse)
async def list_urls(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    offset = (page - 1) * page_size
    total = await session.scalar(select(func.count()).select_from(URL)) or 0
    rows = await session.execute(
        select(URL).order_by(URL.created_at.desc()).offset(offset).limit(page_size)
    )
    urls = rows.scalars().all()

    items = []
    for url in urls:
        sub_row = await session.scalar(
            select(VMRaySubmission).where(VMRaySubmission.url_id == url.id)
        )
        items.append(
            URLOut(
                id=url.id,
                url_hash=url.url_hash,
                original_defanged=url.original_defanged,
                normalized_url=url.normalized_url,
                vt_comment_id=url.vt_comment_id,
                status=url.status,
                created_at=url.created_at,
                updated_at=url.updated_at,
                submission=VMRaySubmissionOut.model_validate(sub_row) if sub_row else None,
            )
        )

    return URLListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{url_id}", response_model=URLOut)
async def get_url(url_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    url = await session.get(URL, url_id)
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    sub_row = await session.scalar(
        select(VMRaySubmission).where(VMRaySubmission.url_id == url.id)
    )
    return URLOut(
        id=url.id,
        url_hash=url.url_hash,
        original_defanged=url.original_defanged,
        normalized_url=url.normalized_url,
        vt_comment_id=url.vt_comment_id,
        status=url.status,
        created_at=url.created_at,
        updated_at=url.updated_at,
        submission=VMRaySubmissionOut.model_validate(sub_row) if sub_row else None,
    )
