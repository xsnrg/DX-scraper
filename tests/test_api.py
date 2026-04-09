import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "DXpedition Monitor API"}

def test_get_data():
    """Test the /data endpoint."""
    response = client.get("/data")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)

