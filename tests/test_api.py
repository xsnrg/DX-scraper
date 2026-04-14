import pytest
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    # The root endpoint serves the index.html file, not a JSON response
    assert "DXpedition Monitor" in response.text
def test_get_data():
    """Test the /data endpoint."""
    response = client.get("/data")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)

