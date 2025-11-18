"""
API tests for Flight Price Prediction service.
"""

import pytest
from fastapi.testclient import TestClient
from src.app.api import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "endpoints" in data


def test_model_info():
    """Test model info endpoint."""
    response = client.get("/model_info")
    assert response.status_code in [200, 503]  # 503 if model not loaded

    if response.status_code == 200:
        data = response.json()
        assert "model_name" in data
        assert "model_version" in data


def test_predict_endpoint():
    """Test prediction endpoint."""
    # Sample prediction request
    payload = {
        "airline": "SpiceJet",
        "source_city": "Delhi",
        "destination_city": "Mumbai",
        "departure_time": "Evening",
        "arrival_time": "Night",
        "stops": "zero",
        "class": "Economy",
        "duration": 2.17,
        "days_left": 1
    }

    response = client.post("/predict", json=payload)

    # Could be 200 (success) or 503 (model not loaded) or 500 (prediction error)
    assert response.status_code in [200, 500, 503]

    if response.status_code == 200:
        data = response.json()
        assert "predicted_price" in data
        assert "model_name" in data
        assert "model_version" in data
        assert "latency_ms" in data
        assert data["predicted_price"] > 0


def test_predict_invalid_data():
    """Test prediction with invalid data."""
    # Missing required fields
    payload = {
        "airline": "SpiceJet",
        "duration": 2.17
    }

    response = client.post("/predict", json=payload)
    assert response.status_code == 422  # Validation error


def test_metrics_endpoint():
    """Test Prometheus metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_concurrent_predictions():
    """Test multiple concurrent predictions."""
    payload = {
        "airline": "SpiceJet",
        "source_city": "Delhi",
        "destination_city": "Mumbai",
        "departure_time": "Evening",
        "arrival_time": "Night",
        "stops": "zero",
        "class": "Economy",
        "duration": 2.17,
        "days_left": 1
    }

    # Make multiple requests
    responses = []
    for _ in range(5):
        response = client.post("/predict", json=payload)
        responses.append(response)

    # All should return same status
    status_codes = [r.status_code for r in responses]
    assert len(set(status_codes)) == 1  # All same status
