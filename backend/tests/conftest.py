"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet

os.environ.setdefault("SECRET_KEY", "pytest-secret-key-not-default")
os.environ.setdefault("ENCRYPTION_KEY", Fernet.generate_key().decode())
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_saidas.db")
os.environ.setdefault("PLAYWRIGHT_HEADLESS", "true")

from app.core.config import get_settings

get_settings.cache_clear()

from app.core.rate_limit import limiter

limiter.enabled = False

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db, init_db
from app.main import app

_test_engine = create_engine(
    os.environ["DATABASE_URL"],
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=_test_engine)
    init_db()
    yield


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    client.post(
        "/auth/register",
        json={
            "ra": "123456",
            "password": "secret123",
            "profile": "Aluno Graduação",
            "full_name": "Test User",
        },
    )
    response = client.post(
        "/auth/login",
        data={"username": "123456", "password": "secret123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
