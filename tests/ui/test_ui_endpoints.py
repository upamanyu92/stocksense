import pytest

pytestmark = pytest.mark.ui


def test_login_page_renders(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"login" in response.data.lower()


def test_register_page_renders(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"register" in response.data.lower()


def test_dashboard_requires_auth(client):
    response = client.get("/dashboard")
    assert response.status_code in (302, 401)


def test_stocks_page_requires_auth(client):
    response = client.get("/stocks")
    assert response.status_code in (302, 401)


def test_premium_page_renders_for_logged_in_user(logged_in_client):
    response = logged_in_client.get("/premium")
    assert response.status_code == 200
    assert b"stocksense" in response.data.lower()
    assert b"premium" in response.data.lower()
