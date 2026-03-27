from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="module")
def client(db_engine):
    SessionTest = sessionmaker(bind=db_engine)

    def override_get_db():
        session = SessionTest()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="module", autouse=True)
def mock_redis():
    with patch("app.cache.redis_client") as mock:
        mock.get.return_value = None
        mock.setex.return_value = True
        mock.delete.return_value = 1
        yield mock


@pytest.fixture
def api_product(client):
    response = client.post(
        "/products/",
        json={
            "name": "Clavier Mécanique",
            "price": 89.99,
            "stock": 25,
            "category": "peripheriques",
        },
    )
    assert response.status_code == 201
    yield response.json()
    client.delete(f"/products/{response.json()['id']}")


@pytest.fixture
def api_coupon(client):
    response = client.post(
        "/coupons/", json={"code": "TEST10", "reduction": 10.0, "actif": True}
    )
    assert response.status_code == 201
    yield response.json()
