import math
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from app.api.stats import stats_summary
from app.api.urls import list_urls, get_url
from app.deps import get_session

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    summary = await stats_summary(session=session)
    return templates.TemplateResponse(
        request, "dashboard.html", {"summary": summary}
    )


@router.get("/urls/view", response_class=HTMLResponse)
async def urls_list_view(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    verdict: str | None = Query(None),
    domain: str | None = Query(None),
    q: str | None = Query(None),
    sort: Literal["newest", "oldest", "updated"] = Query("newest"),
    session: AsyncSession = Depends(get_session),
):
    result = await list_urls(
        page=page,
        page_size=page_size,
        status=status,
        verdict=verdict,
        domain=domain,
        q=q,
        sort=sort,
        session=session,
    )
    total_pages = max(1, math.ceil(result.total / page_size))

    # Build query string without page for pagination links
    params = dict(request.query_params)
    params.pop("page", None)
    qs = "&".join(f"{k}={v}" for k, v in params.items())

    return templates.TemplateResponse(
        request,
        "urls_list.html",
        {
            "urls": result.items,
            "total": result.total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "status": status,
            "verdict": verdict,
            "domain": domain,
            "q": q,
            "sort": sort,
            "query_string": qs,
        },
    )


@router.get("/urls/view/{url_id}", response_class=HTMLResponse)
async def url_detail_view(
    request: Request,
    url_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    url = await get_url(url_id=url_id, session=session)
    return templates.TemplateResponse(
        request, "url_detail.html", {"url": url}
    )
