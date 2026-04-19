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


def _make_vt_comment_data(comment_id: str, content: str) -> VTCommentData:
    return VTCommentData(
        comment_id=comment_id,
        author="tester",
        content=content,
        published_at=None,
        raw={"id": comment_id, "attributes": {"text": content}},
    )


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
    client.submit_url = AsyncMock(return_value={"submission_id": "sub-123"})
    client.get_submission = AsyncMock(return_value={
        "data": {"verdict": "malicious", "submission_status": "finished"}
    })
    return client


async def test_vt_pipeline_disabled_when_not_configured(db_session):
    client = MagicMock()
    client.is_configured = False
    result = await VTPipeline(db_session, client).run()
    assert result["status"] == "disabled"
    assert result["fetched"] == 0


async def test_vt_pipeline_stores_new_comments(db_session, mock_vt_client):
    cid = f"test-comment-{uuid.uuid4()}"
    mock_vt_client.get_comments = AsyncMock(
        return_value=([_make_vt_comment_data(cid, "clickfix payload at hxxp://bad[.]com/x")], None)
    )
    result = await VTPipeline(db_session, mock_vt_client).run()
    assert result["status"] == "ok"
    assert result["fetched"] == 1
    assert result["new"] == 1

    stored = await db_session.scalar(select(VTComment).where(VTComment.comment_id == cid))
    assert stored is not None
    assert stored.author == "tester"


async def test_vt_pipeline_skips_existing_comments(db_session, mock_vt_client):
    cid = f"existing-{uuid.uuid4()}"
    mock_vt_client.get_comments = AsyncMock(
        return_value=([_make_vt_comment_data(cid, "text")], None)
    )
    # Insert first time
    await VTPipeline(db_session, mock_vt_client).run()
    # Insert second time — should skip
    result = await VTPipeline(db_session, mock_vt_client).run()
    assert result["new"] == 0


async def test_url_process_pipeline_extracts_urls(db_session, mock_vt_client):
    cid = f"url-test-{uuid.uuid4()}"
    mock_vt_client.get_comments = AsyncMock(
        return_value=([_make_vt_comment_data(cid, "hxxps://malware[.]io/stage2 is bad")], None)
    )
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
    cid = f"dup-test-{uuid.uuid4()}"
    mock_vt_client.get_comments = AsyncMock(
        return_value=([_make_vt_comment_data(cid, "hxxp://dup[.]site/x")], None)
    )
    await VTPipeline(db_session, mock_vt_client).run()

    result1 = await URLProcessPipeline(db_session).run()
    result2 = await URLProcessPipeline(db_session).run()
    assert result2["new_urls"] == 0


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
        submission_id="sub-poll-001",
    )
    db_session.add(sub)
    await db_session.commit()

    mock_vmray_client.get_submission = AsyncMock(return_value={
        "data": {"verdict": "malicious", "submission_status": "finished"}
    })

    result = await VMRayPollPipeline(db_session, mock_vmray_client).run()
    assert result["status"] == "ok"
    assert result["completed"] >= 1

    await db_session.refresh(url_obj)
    assert url_obj.status == "done"
