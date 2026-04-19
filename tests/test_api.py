import uuid

import pytest


def test_health_db_ok(db_client):
    response = db_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "db": "ok"}


def test_health_db_down(no_db_client):
    response = no_db_client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "healthy", "db": "error"}


def test_stats_summary_empty(db_client):
    response = db_client.get("/stats/summary")
    assert response.status_code == 200
    body = response.json()
    assert "total_comments" in body
    assert "total_urls" in body
    assert "total_unique_normalized_urls" in body
    assert "url_statuses" in body
    assert "total_submissions" in body
    assert "completed_submissions" in body
    assert "verdict_counts" in body
    assert "top_domains" in body
    assert "latest_comment_at" in body
    assert "latest_url_at" in body
    assert "latest_submission_at" in body
    assert body["total_comments"] >= 0
    vc = body["verdict_counts"]
    assert "malicious" in vc
    assert "suspicious" in vc
    assert "clean" in vc
    assert "unknown" in vc
    assert isinstance(body["top_domains"], list)


def test_list_urls_empty(db_client):
    response = db_client.get("/urls")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body
    assert "page_size" in body
    assert body["page"] == 1
    assert body["page_size"] == 20


def test_list_urls_item_shape(db_client, db_session):
    """URLOut items must include source and must not include score."""
    import asyncio
    from app.models.url import URL as URLModel
    from app.models.vt_comment import VTComment

    async def _setup():
        comment = VTComment(
            id=uuid.uuid4(),
            comment_id=f"c-{uuid.uuid4().hex}",
            author="analyst1",
            content="hxxp://shape[.]test/x",
        )
        db_session.add(comment)
        await db_session.flush()
        url = URLModel(
            id=uuid.uuid4(),
            url_hash=f"hash-{uuid.uuid4().hex}",
            original_defanged="hxxp://shape[.]test/x",
            normalized_url="http://shape.test/x",
            domain="shape.test",
            scheme="http",
            vt_comment_id=comment.id,
            status="pending",
        )
        db_session.add(url)
        await db_session.commit()

    asyncio.get_event_loop().run_until_complete(_setup())

    response = db_client.get("/urls?q=shape.test")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    item = items[0]
    assert "source" in item
    assert item["source"] == "analyst1"
    assert "score" not in item


def test_list_urls_pagination(db_client):
    response = db_client.get("/urls?page=2&page_size=5")
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 5


def test_list_urls_status_filter(db_client):
    response = db_client.get("/urls?status=pending")
    assert response.status_code == 200
    body = response.json()
    for item in body["items"]:
        assert item["status"] == "pending"


def test_list_urls_verdict_filter(db_client):
    response = db_client.get("/urls?verdict=malicious")
    assert response.status_code == 200
    body = response.json()
    for item in body["items"]:
        assert item["verdict"] == "malicious"


def test_list_urls_sort_oldest(db_client):
    response = db_client.get("/urls?sort=oldest")
    assert response.status_code == 200
    assert response.json()["page"] == 1


def test_list_urls_sort_updated(db_client):
    response = db_client.get("/urls?sort=updated")
    assert response.status_code == 200


def test_list_urls_search(db_client):
    response = db_client.get("/urls?q=example")
    assert response.status_code == 200
    body = response.json()
    for item in body["items"]:
        assert "example" in item["normalized_url"]


def test_list_urls_domain_filter(db_client):
    response = db_client.get("/urls?domain=nonexistent.example.com")
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_get_url_not_found(db_client):
    response = db_client.get(f"/urls/{uuid.uuid4()}")
    assert response.status_code == 404


def test_get_url_detail_shape(db_client, db_session):
    """Create a URL and verify the detail endpoint returns all enrichment fields."""
    import asyncio
    from app.models.url import URL as URLModel
    from app.models.vt_comment import VTComment

    async def _setup():
        comment = VTComment(
            id=uuid.uuid4(),
            comment_id=f"c-{uuid.uuid4().hex}",
            author="",
            content="test hxxp://detail[.]test/path",
        )
        db_session.add(comment)
        await db_session.flush()
        url = URLModel(
            id=uuid.uuid4(),
            url_hash=f"hash-{uuid.uuid4().hex}",
            original_defanged="hxxp://detail[.]test/path",
            normalized_url="http://detail.test/path",
            domain="detail.test",
            scheme="http",
            vt_comment_id=comment.id,
            status="pending",
        )
        db_session.add(url)
        await db_session.commit()
        return str(url.id)

    url_id = asyncio.get_event_loop().run_until_complete(_setup())

    response = db_client.get(f"/urls/{url_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["original_defanged"] == "hxxp://detail[.]test/path"
    assert body["normalized_url"] == "http://detail.test/path"
    assert body["domain"] == "detail.test"
    assert body["scheme"] == "http"
    assert body["status"] == "pending"
    assert "source_comment" in body
    assert body["source_comment"] is not None
    assert "test hxxp://detail[.]test/path" in body["source_comment"]["content"]
    assert "submission" in body


def test_internal_vt_poll_disabled(db_client):
    response = db_client.post("/internal/vt/poll")
    assert response.status_code == 200
    body = response.json()
    assert body["vt"]["status"] == "disabled"


def test_internal_urls_extract(db_client):
    response = db_client.post("/internal/urls/extract")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "processed" in body
    assert "new_urls" in body


def test_internal_vmray_submit_disabled(db_client):
    response = db_client.post("/internal/vmray/submit")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "disabled"


def test_internal_vmray_poll_disabled(db_client):
    response = db_client.post("/internal/vmray/poll")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "disabled"


# UI pages

def test_dashboard_page_returns_200(db_client):
    response = db_client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"Dashboard" in response.content


def test_urls_view_page_returns_200(db_client):
    response = db_client.get("/urls/view")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_urls_view_with_filters_returns_200(db_client):
    response = db_client.get("/urls/view?status=pending&sort=oldest")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_urls_view_detail_not_found(db_client):
    response = db_client.get(f"/urls/view/{uuid.uuid4()}")
    assert response.status_code == 404
