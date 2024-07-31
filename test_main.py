from fastapi.testclient import TestClient
from main import app, calculate_square

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome my site"}


def test_calculate_square():
    assert calculate_square(3) == 9
    assert calculate_square(0) == 0
    assert calculate_square(-4) == 16
    assert calculate_square(1.5) == 2.25

def test_square_endpoint():
    response = client.get("/square?number=3")
    assert response.status_code == 200
    assert response.json() == {"number": 3, "square": 9}

    response = client.get("/square?number=0")
    assert response.status_code == 200
    assert response.json() == {"number": 0, "square": 0}

    response = client.get("/square?number=-4")
    assert response.status_code == 200
    assert response.json() == {"number": -4, "square": 16}

    response = client.get("/square?number=1.5")
    assert response.status_code == 200
    assert response.json() == {"number": 1.5, "square": 2.25}