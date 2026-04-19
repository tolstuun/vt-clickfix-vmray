def test_health_db_ok(db_client):
    response = db_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "db": "ok"}


def test_health_db_down(no_db_client):
    response = no_db_client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "healthy", "db": "error"}
