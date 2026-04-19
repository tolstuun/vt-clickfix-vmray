import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.models.url import URL
from app.models.vmray_submission import VMRaySubmission
from app.models.vt_comment import VTComment
from app.schemas.url import URLDetailOut, URLListResponse, URLOut, VMRaySubmissionOut, VTCommentRef

router = APIRouter(prefix="/urls")


def _build_submission_out(sub: VMRaySubmission | None) -> VMRaySubmissionOut | None:
    if sub is None:
        return None
    return VMRaySubmissionOut.model_validate(sub)


def _source_label(comment: VTComment | None) -> str | None:
    if comment is None:
        return None
    if comment.author:
        return comment.author
    return comment.comment_id


async def _load_source(session: AsyncSession, url: URL) -> str | None:
    if not url.vt_comment_id:
        return None
    comment = await session.get(VTComment, url.vt_comment_id)
    return _source_label(comment)


def _url_to_out(url: URL, sub: VMRaySubmission | None, source: str | None) -> URLOut:
    return URLOut(
        id=url.id,
        normalized_url=url.normalized_url,
        domain=url.domain,
        status=url.status,
        source=source,
        verdict=sub.verdict if sub else None,
        report_url=sub.report_url if sub else None,
        created_at=url.created_at,
        updated_at=url.updated_at,
        submission=_build_submission_out(sub),
    )


@router.get("", response_model=URLListResponse)
async def list_urls(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by URL status"),
    verdict: str | None = Query(None, description="Filter by VMRay verdict"),
    domain: str | None = Query(None, description="Filter by domain (exact match)"),
    q: str | None = Query(None, description="Search normalized_url substring"),
    sort: Literal["newest", "oldest", "updated"] = Query("newest"),
    session: AsyncSession = Depends(get_session),
):
    base_query = select(URL)

    if verdict is not None:
        base_query = base_query.join(VMRaySubmission, VMRaySubmission.url_id == URL.id).where(
            VMRaySubmission.verdict == verdict
        )
    if status is not None:
        base_query = base_query.where(URL.status == status)
    if domain is not None:
        base_query = base_query.where(URL.domain == domain)
    if q is not None:
        base_query = base_query.where(URL.normalized_url.ilike(f"%{q}%"))

    count_query = select(func.count()).select_from(base_query.subquery())
    total = await session.scalar(count_query) or 0

    if sort == "oldest":
        order = URL.created_at.asc()
    elif sort == "updated":
        order = URL.updated_at.desc()
    else:
        order = URL.created_at.desc()

    offset = (page - 1) * page_size
    rows = await session.execute(
        base_query.order_by(order).offset(offset).limit(page_size)
    )
    urls = rows.scalars().all()

    items = []
    for url in urls:
        sub = await session.scalar(
            select(VMRaySubmission).where(VMRaySubmission.url_id == url.id)
        )
        source = await _load_source(session, url)
        items.append(_url_to_out(url, sub, source))

    return URLListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{url_id}", response_model=URLDetailOut)
async def get_url(url_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    url = await session.get(URL, url_id)
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")

    sub = await session.scalar(
        select(VMRaySubmission).where(VMRaySubmission.url_id == url.id)
    )

    source_comment = None
    if url.vt_comment_id:
        comment = await session.get(VTComment, url.vt_comment_id)
        if comment:
            source_comment = VTCommentRef.model_validate(comment)

    return URLDetailOut(
        id=url.id,
        original_defanged=url.original_defanged,
        normalized_url=url.normalized_url,
        domain=url.domain,
        scheme=url.scheme,
        status=url.status,
        created_at=url.created_at,
        updated_at=url.updated_at,
        source_comment=source_comment,
        submission=_build_submission_out(sub),
    )
