from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.models.url import URL
from app.models.vmray_submission import VMRaySubmission
from app.models.vt_comment import VTComment
from app.schemas.stats import StatsSummary, URLStatusCounts

router = APIRouter(prefix="/stats")


@router.get("/summary", response_model=StatsSummary)
async def stats_summary(session: AsyncSession = Depends(get_session)):
    total_comments = await session.scalar(select(func.count()).select_from(VTComment)) or 0
    total_urls = await session.scalar(select(func.count()).select_from(URL)) or 0
    total_submissions = await session.scalar(select(func.count()).select_from(VMRaySubmission)) or 0
    completed_submissions = (
        await session.scalar(
            select(func.count()).select_from(VMRaySubmission).where(
                VMRaySubmission.completed_at.is_not(None)
            )
        )
        or 0
    )

    status_rows = await session.execute(
        select(URL.status, func.count()).group_by(URL.status)
    )
    status_counts = {row[0]: row[1] for row in status_rows}

    return StatsSummary(
        total_comments=total_comments,
        total_urls=total_urls,
        url_statuses=URLStatusCounts(
            pending=status_counts.get("pending", 0),
            submitted=status_counts.get("submitted", 0),
            analyzing=status_counts.get("analyzing", 0),
            done=status_counts.get("done", 0),
            failed=status_counts.get("failed", 0),
        ),
        total_submissions=total_submissions,
        completed_submissions=completed_submissions,
    )
