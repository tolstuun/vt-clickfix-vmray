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
    assert "url_statuses" in body
    assert "total_submissions" in body
    assert "completed_submissions" in body
    assert body["total_comments"] >= 0


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


def test_list_urls_pagination(db_client):
    response = db_client.get("/urls?page=2&page_size=5")
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["page_size"] == 5


def test_get_url_not_found(db_client):
    response = db_client.get(f"/urls/{uuid.uuid4()}")
    assert response.status_code == 404


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
