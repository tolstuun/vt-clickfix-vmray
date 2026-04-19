"""Pipeline integration tests.

Mock payloads match actual API contracts:
- VT: GET /api/v3/comments response schema (meta.cursor, data[].attributes.{text,date,tags,votes})
- VMRay submit: POST /rest/sample/submit → SampleSubmit schema
  { "result": "ok", "data": { "submissions": [{"submission_id": int, ...}], ... } }
- VMRay poll: GET /rest/submission/<id> → SubmissionItem schema
  { "result": "ok", "data": { "submission_id": int, "submission_finished": bool,
                               "submission_verdict": str|null, "submission_score": int|null, ... } }
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select

from app.models.url import URL
from app.models.vt_comment import VTComment
from app.models.vmray_submission import VMRaySubmission
from app.services.pipeline import (
    URLProcessPipeline,
    VMRayPollPipeline,
    VMRaySubmitPipeline,
    VTPipeline,
)
from app.services.vt_client import VTCommentData

# ---------------------------------------------------------------------------
# Realistic mock payloads (matching documented API schemas)
# ---------------------------------------------------------------------------

def _vt_comment_response(comment_id: str, text: str, tags: list[str] | None = None) -> dict:
    """Mimics a VT GET /api/v3/comments data item."""
    return {
        "type": "comment",
        "id": comment_id,
        "attributes": {
            "text": text,
            "html": f"<p>{text}</p>",
            "date": 1713484800,  # 2024-04-19 00:00:00 UTC
            "tags": tags or ["clickfix"],
            "votes": {"positive": 3, "negative": 0, "abuse": 0},
        },
        "links": {"self": f"https://www.virustotal.com/api/v3/comments/{comment_id}"},
    }


def _vt_comments_page(comment_id: str, text: str, cursor: str | None = None) -> tuple:
    """Returns (list[VTCommentData], next_cursor) matching VTClient.get_comments output."""
    item = _vt_comment_response(comment_id, text)
    data = VTCommentData(
        comment_id=comment_id,
        author="",  # not in documented API
        content=text,
        published_at=None,
        raw=item,
    )
    return [data], cursor


def _vmray_submit_response(submission_id: int = 98765) -> dict:
    """Mimics POST /rest/sample/submit → SampleSubmit schema."""
    return {
        "result": "ok",
        "data": {
            "errors": [],
            "jobs": [],
            "static_jobs": [],
            "reputation_jobs": [],
            "samples": [{"sample_id": 11111}],
            "submissions": [
                {
                    "submission_id": submission_id,
                    "submission_finished": False,
                    "submission_verdict": None,
                    "submission_score": None,
                    "submission_filename": "https://example.com/",
                }
            ],
        },
        "continuation_id": None,
        "truncated": False,
    }


def _vmray_poll_response(
    submission_id: int = 98765,
    finished: bool = True,
    verdict: str | None = "malicious",
    score: int | None = 100,
) -> dict:
    """Mimics GET /rest/submission/<id> → SubmissionItem schema."""
    return {
        "result": "ok",
        "data": {
            "submission_id": submission_id,
            "submission_finished": finished,
            "submission_verdict": verdict,
            "submission_score": score,
            "submission_sample_verdict": verdict,
            "submission_filename": "https://example.com/",
            "submission_status": "inwork" if not finished else "finished",
        },
        "continuation_id": None,
        "truncated": False,
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_vt_client():
    client = MagicMock()
    client.is_configured = True
    client.get_comments = AsyncMock(return_value=([], None))
    return client


@pytest.fixture
def mock_vmray_client():
    client = MagicMock()
    client.is_configured = True
    client.submit_url = AsyncMock(return_value=_vmray_submit_response())
    client.get_submission = AsyncMock(return_value=_vmray_poll_response())
    return client


# ---------------------------------------------------------------------------
# VTPipeline tests
# ---------------------------------------------------------------------------

async def test_vt_pipeline_disabled_when_not_configured(db_session):
    client = MagicMock()
    client.is_configured = False
    result = await VTPipeline(db_session, client).run()
    assert result["status"] == "disabled"
    assert result["fetched"] == 0


async def test_vt_pipeline_stores_new_comments(db_session, mock_vt_client):
    cid = f"u-{uuid.uuid4().hex}-abc"
    comments, cursor = _vt_comments_page(cid, "clickfix payload at hxxp://bad[.]com/x")
    mock_vt_client.get_comments = AsyncMock(return_value=(comments, cursor))

    result = await VTPipeline(db_session, mock_vt_client).run()
    assert result["status"] == "ok"
    assert result["fetched"] == 1
    assert result["new"] == 1

    stored = await db_session.scalar(select(VTComment).where(VTComment.comment_id == cid))
    assert stored is not None
    assert stored.author == ""  # not in documented VT API response
    # raw_response stores the full documented VT comment item
    assert stored.raw_response["attributes"]["tags"] == ["clickfix"]
    assert stored.raw_response["attributes"]["votes"]["positive"] == 3


async def test_vt_pipeline_skips_existing_comments(db_session, mock_vt_client):
    cid = f"u-{uuid.uuid4().hex}-abc"
    comments, _ = _vt_comments_page(cid, "some text")
    mock_vt_client.get_comments = AsyncMock(return_value=(comments, None))

    await VTPipeline(db_session, mock_vt_client).run()
    result = await VTPipeline(db_session, mock_vt_client).run()
    assert result["new"] == 0


async def test_vt_pipeline_stores_raw_response(db_session, mock_vt_client):
    cid = f"u-{uuid.uuid4().hex}-raw"
    item = _vt_comment_response(cid, "hxxp://example[.]com/path")
    data = VTCommentData(comment_id=cid, author="", content=item["attributes"]["text"],
                         published_at=None, raw=item)
    mock_vt_client.get_comments = AsyncMock(return_value=([data], None))

    await VTPipeline(db_session, mock_vt_client).run()
    stored = await db_session.scalar(select(VTComment).where(VTComment.comment_id == cid))
    assert stored.raw_response["type"] == "comment"
    assert stored.raw_response["id"] == cid


# ---------------------------------------------------------------------------
# URLProcessPipeline tests
# ---------------------------------------------------------------------------

async def test_url_process_pipeline_extracts_urls(db_session, mock_vt_client):
    cid = f"u-{uuid.uuid4().hex}-url"
    comments, _ = _vt_comments_page(cid, "hxxps://malware[.]io/stage2 is bad")
    mock_vt_client.get_comments = AsyncMock(return_value=(comments, None))
    await VTPipeline(db_session, mock_vt_client).run()

    result = await URLProcessPipeline(db_session).run()
    assert result["status"] == "ok"
    assert result["new_urls"] >= 1

    url = await db_session.scalar(
        select(URL).where(URL.normalized_url == "https://malware.io/stage2")
    )
    assert url is not None
    assert url.status == "pending"


async def test_url_process_pipeline_deduplicates(db_session, mock_vt_client):
    cid = f"u-{uuid.uuid4().hex}-dup"
    comments, _ = _vt_comments_page(cid, "hxxp://dup[.]site/x")
    mock_vt_client.get_comments = AsyncMock(return_value=(comments, None))
    await VTPipeline(db_session, mock_vt_client).run()

    result1 = await URLProcessPipeline(db_session).run()
    result2 = await URLProcessPipeline(db_session).run()
    assert result2["new_urls"] == 0


# ---------------------------------------------------------------------------
# VMRaySubmitPipeline tests
# ---------------------------------------------------------------------------

async def test_vmray_submit_pipeline_disabled(db_session):
    client = MagicMock()
    client.is_configured = False
    result = await VMRaySubmitPipeline(db_session, client).run()
    assert result["status"] == "disabled"


async def test_vmray_submit_pipeline_submits_pending(db_session, mock_vmray_client):
    url_obj = URL(
        id=uuid.uuid4(),
        url_hash=f"hash-{uuid.uuid4().hex}",
        original_defanged="hxxp://submit[.]test/x",
        normalized_url="http://submit.test/x",
        status="pending",
    )
    db_session.add(url_obj)
    await db_session.commit()

    result = await VMRaySubmitPipeline(db_session, mock_vmray_client).run()
    assert result["status"] == "ok"
    assert result["submitted"] >= 1

    await db_session.refresh(url_obj)
    assert url_obj.status == "submitted"

    sub = await db_session.scalar(
        select(VMRaySubmission).where(VMRaySubmission.url_id == url_obj.id)
    )
    assert sub is not None
    # submission_id extracted from data.submissions[0].submission_id
    assert sub.submission_id == "98765"


async def test_vmray_submit_stores_full_raw_response(db_session, mock_vmray_client):
    url_obj = URL(
        id=uuid.uuid4(),
        url_hash=f"hash-{uuid.uuid4().hex}",
        original_defanged="hxxp://rawstore[.]test/x",
        normalized_url="http://rawstore.test/x",
        status="pending",
    )
    db_session.add(url_obj)
    await db_session.commit()

    await VMRaySubmitPipeline(db_session, mock_vmray_client).run()

    sub = await db_session.scalar(
        select(VMRaySubmission).where(VMRaySubmission.url_id == url_obj.id)
    )
    assert sub.raw_response["result"] == "ok"
    assert "submissions" in sub.raw_response["data"]


# ---------------------------------------------------------------------------
# VMRayPollPipeline tests
# ---------------------------------------------------------------------------

async def test_vmray_poll_pipeline_disabled(db_session):
    client = MagicMock()
    client.is_configured = False
    result = await VMRayPollPipeline(db_session, client).run()
    assert result["status"] == "disabled"


async def test_vmray_poll_pipeline_completes_submission(db_session, mock_vmray_client):
    url_obj = URL(
        id=uuid.uuid4(),
        url_hash=f"hash-{uuid.uuid4().hex}",
        original_defanged="hxxp://poll[.]test/x",
        normalized_url="http://poll.test/x",
        status="submitted",
    )
    db_session.add(url_obj)
    await db_session.flush()

    sub = VMRaySubmission(
        id=uuid.uuid4(),
        url_id=url_obj.id,
        submission_id="98765",
    )
    db_session.add(sub)
    await db_session.commit()

    mock_vmray_client.get_submission = AsyncMock(
        return_value=_vmray_poll_response(submission_id=98765, finished=True,
                                          verdict="malicious", score=100)
    )

    result = await VMRayPollPipeline(db_session, mock_vmray_client).run()
    assert result["status"] == "ok"
    assert result["completed"] >= 1

    await db_session.refresh(url_obj)
    assert url_obj.status == "done"
    await db_session.refresh(sub)
    assert sub.verdict == "malicious"
    assert sub.score == 100
    assert sub.completed_at is not None


async def test_vmray_poll_pipeline_not_finished_yet(db_session, mock_vmray_client):
    """When submission_finished=False, URL stays submitted and completed count is 0."""
    url_obj = URL(
        id=uuid.uuid4(),
        url_hash=f"hash-{uuid.uuid4().hex}",
        original_defanged="hxxp://pending[.]test/x",
        normalized_url="http://pending.test/x",
        status="submitted",
    )
    db_session.add(url_obj)
    await db_session.flush()

    sub = VMRaySubmission(
        id=uuid.uuid4(),
        url_id=url_obj.id,
        submission_id="11111",
    )
    db_session.add(sub)
    await db_session.commit()

    mock_vmray_client.get_submission = AsyncMock(
        return_value=_vmray_poll_response(
            submission_id=11111, finished=False, verdict=None, score=None
        )
    )

    result = await VMRayPollPipeline(db_session, mock_vmray_client).run()
    assert result["completed"] == 0

    await db_session.refresh(url_obj)
    assert url_obj.status == "submitted"  # unchanged
    await db_session.refresh(sub)
    assert sub.completed_at is None
