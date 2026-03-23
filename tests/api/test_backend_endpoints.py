import pytest

pytestmark = pytest.mark.api


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_dashboard_overview_requires_auth(client):
    response = client.get("/api/dashboard/overview")
    assert response.status_code in (302, 401)


def test_dashboard_overview_logged_in(logged_in_client):
    response = logged_in_client.get("/api/dashboard/overview")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    assert payload["overview"]["holdings_count"] >= 1


def test_market_indices_logged_in(logged_in_client):
    response = logged_in_client.get("/api/dashboard/market-indices")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    assert len(payload["indices"]) >= 1


def test_predictions_summary_logged_in(logged_in_client):
    response = logged_in_client.get("/api/dashboard/predictions-summary")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    assert isinstance(payload["predictions"], list)


def test_system_background_status_public(client):
    response = client.get("/api/system/background-status")
    assert response.status_code == 200
    assert isinstance(response.get_json(), dict)
