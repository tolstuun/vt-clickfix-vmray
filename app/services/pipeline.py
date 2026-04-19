import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URL
from app.models.vmray_submission import VMRaySubmission
from app.models.vt_comment import VTComment
from app.services.url_extractor import extract_urls, url_hash
from app.services.vt_client import VTClient
from app.services.vmray_client import VMRayClient


class VTPipeline:
    def __init__(self, session: AsyncSession, vt_client: VTClient) -> None:
        self._session = session
        self._vt = vt_client

    async def run(self) -> dict:
        if not self._vt.is_configured:
            return {"status": "disabled", "fetched": 0, "new": 0}

        comments, _ = await self._vt.get_comments()
        fetched = len(comments)
        new = 0

        for c in comments:
            existing = await self._session.scalar(
                select(VTComment).where(VTComment.comment_id == c.comment_id)
            )
            if existing:
                continue
            self._session.add(
                VTComment(
                    id=uuid.uuid4(),
                    comment_id=c.comment_id,
                    author=c.author,
                    content=c.content,
                    published_at=c.published_at,
                    raw_response=c.raw,
                )
            )
            new += 1

        await self._session.commit()
        return {"status": "ok", "fetched": fetched, "new": new}


class URLProcessPipeline:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def run(self) -> dict:
        result = await self._session.execute(select(VTComment))
        comments = result.scalars().all()

        processed = 0
        new_urls = 0

        for comment in comments:
            for original, normalized in extract_urls(comment.content):
                h = url_hash(normalized)
                existing = await self._session.scalar(
                    select(URL).where(URL.url_hash == h)
                )
                if existing:
                    continue
                self._session.add(
                    URL(
                        id=uuid.uuid4(),
                        url_hash=h,
                        original_defanged=original,
                        normalized_url=normalized,
                        vt_comment_id=comment.id,
                        status="pending",
                    )
                )
                new_urls += 1
            processed += 1

        await self._session.commit()
        return {"status": "ok", "processed": processed, "new_urls": new_urls}


class VMRaySubmitPipeline:
    def __init__(self, session: AsyncSession, vmray_client: VMRayClient) -> None:
        self._session = session
        self._vmray = vmray_client

    async def run(self) -> dict:
        if not self._vmray.is_configured:
            return {"status": "disabled", "submitted": 0}

        result = await self._session.execute(
            select(URL).where(URL.status == "pending")
        )
        pending_urls = result.scalars().all()

        submitted = 0
        for url in pending_urls:
            try:
                raw = await self._vmray.submit_url(url.normalized_url)
            except Exception:
                url.status = "failed"
                continue

            # SampleSubmit response: data.submissions[0].submission_id (int)
            subs = raw.get("data", {}).get("submissions", [])
            submission_id = str(subs[0]["submission_id"]) if subs else None
            self._session.add(
                VMRaySubmission(
                    id=uuid.uuid4(),
                    url_id=url.id,
                    submission_id=submission_id or None,
                    raw_response=raw,
                )
            )
            url.status = "submitted"
            submitted += 1

        await self._session.commit()
        return {"status": "ok", "submitted": submitted}


class VMRayPollPipeline:
    def __init__(self, session: AsyncSession, vmray_client: VMRayClient) -> None:
        self._session = session
        self._vmray = vmray_client

    async def run(self) -> dict:
        if not self._vmray.is_configured:
            return {"status": "disabled", "polled": 0, "completed": 0}

        result = await self._session.execute(
            select(VMRaySubmission).where(VMRaySubmission.completed_at.is_(None))
        )
        submissions = result.scalars().all()

        polled = 0
        completed = 0

        for sub in submissions:
            if not sub.submission_id:
                continue
            try:
                raw = await self._vmray.get_submission(sub.submission_id)
            except Exception:
                continue

            polled += 1
            # SubmissionItem response: data is a single Submission object
            data = raw.get("data", {})
            verdict = data.get("submission_verdict")      # VerdictTypeEnum | null
            score = data.get("submission_score")          # int | null
            finished = data.get("submission_finished", False)  # bool

            sub.verdict = verdict
            sub.score = score
            sub.raw_response = raw
            if finished:
                sub.completed_at = datetime.now(tz=timezone.utc)
                url = await self._session.get(URL, sub.url_id)
                if url:
                    url.status = "done"
                completed += 1

        await self._session.commit()
        return {"status": "ok", "polled": polled, "completed": completed}
