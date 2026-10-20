"""
tests/conftest.py — Shared fixtures for AdShield tests.
Uses a temporary SQLite DB per test session.
Sets required env vars (JWT_SECRET, ADMIN_EMAILS) before importing the app.
"""
import os
import sys
import tempfile

import pytest

# Set required env vars BEFORE importing any backend modules
os.environ["JWT_SECRET"] = "test-secret-key-that-is-at-least-32-characters-long"
os.environ["ADMIN_EMAILS"] = "admin@test.com"
os.environ["ENV"] = "development"
os.environ["CORS_ORIGINS"] = "http://localhost:8501"

# Point database to a temp file
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db_path = _tmp_db.name
_tmp_db.close()

# Inject backend into sys.path
backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, os.path.abspath(backend_dir))

# Patch DB_PATH before importing database
import database
database.DB_PATH = _tmp_db_path

from fastapi.testclient import TestClient
from main import app


@pytest.fixture(scope="session", autouse=True)
def init_database():
    """Initialize DB once per test session."""
    database.init_db()
    yield
    # Cleanup
    try:
        os.unlink(_tmp_db_path)
    except OSError:
        pass


@pytest.fixture(scope="session")
def client():
    """Shared test client."""
    return TestClient(app)


@pytest.fixture(scope="session")
def user_a(client):
    """Create user A and return (user_dict, token, headers)."""
    r = client.post("/auth/signup", json={
        "name": "User Alpha",
        "email": "alpha@test.com",
        "password": "securepassword123",
    })
    assert r.status_code == 200
    r2 = client.post("/auth/login", json={
        "email": "alpha@test.com",
        "password": "securepassword123",
    })
    data = r2.json()
    token = data["access_token"]
    return {
        "user": data["user"],
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture(scope="session")
def user_b(client):
    """Create user B and return (user_dict, token, headers)."""
    r = client.post("/auth/signup", json={
        "name": "User Beta",
        "email": "beta@test.com",
        "password": "securepassword456",
    })
    assert r.status_code == 200
    r2 = client.post("/auth/login", json={
        "email": "beta@test.com",
        "password": "securepassword456",
    })
    data = r2.json()
    token = data["access_token"]
    return {
        "user": data["user"],
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture(scope="session")
def admin_user(client):
    """Create admin user and return (user_dict, token, headers)."""
    r = client.post("/auth/signup", json={
        "name": "Admin User",
        "email": "admin@test.com",
        "password": "adminpassword123",
    })
    assert r.status_code == 200
    r2 = client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "adminpassword123",
    })
    data = r2.json()
    token = data["access_token"]
    return {
        "user": data["user"],
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }
