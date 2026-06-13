"""
tests/test_auth.py
------------------
Tests for user registration and login endpoints.

Uses httpx's AsyncClient to test FastAPI endpoints in-process
without needing a running server.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app


# ── pytest configuration ──────────────────────────────────────────────────────
# pytest-asyncio needs this to run async tests
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    """Provide an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


# ─────────────────────────────────────────────────────────────────────────────
# REGISTRATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistration:

    async def test_register_success(self, client: AsyncClient):
        """A new user can register with valid credentials."""
        response = await client.post("/auth/register", json={
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "securepassword123",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "testuser@example.com"
        assert "hashed_password" not in data  # Never expose this

    async def test_register_duplicate_email(self, client: AsyncClient):
        """Registering with a duplicate email returns 409."""
        payload = {
            "username": "user_a",
            "email": "dup@example.com",
            "password": "password123",
        }
        await client.post("/auth/register", json=payload)
        # Second registration with same email
        payload["username"] = "user_b"
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 409

    async def test_register_short_password(self, client: AsyncClient):
        """Password shorter than 8 characters should fail validation."""
        response = await client.post("/auth/register", json={
            "username": "shortpwd",
            "email": "shortpwd@example.com",
            "password": "short",
        })
        assert response.status_code == 422  # Pydantic validation error

    async def test_register_invalid_email(self, client: AsyncClient):
        """Invalid email format should fail validation."""
        response = await client.post("/auth/register", json={
            "username": "bademail",
            "email": "not-an-email",
            "password": "password123",
        })
        assert response.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestLogin:

    async def test_login_success(self, client: AsyncClient):
        """Valid credentials return access + refresh tokens."""
        # Register first
        await client.post("/auth/register", json={
            "username": "loginuser",
            "email": "login@example.com",
            "password": "mypassword123",
        })

        response = await client.post("/auth/login", json={
            "email": "login@example.com",
            "password": "mypassword123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        """Wrong password returns 401."""
        await client.post("/auth/register", json={
            "username": "wrongpwd",
            "email": "wrongpwd@example.com",
            "password": "correct_password",
        })
        response = await client.post("/auth/login", json={
            "email": "wrongpwd@example.com",
            "password": "wrong_password",
        })
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Login with non-existent email returns 401."""
        response = await client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "anypassword",
        })
        assert response.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# PROTECTED ROUTE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestProtectedRoutes:

    async def test_get_me_without_token(self, client: AsyncClient):
        """Accessing /users/me without token returns 401."""
        response = await client.get("/users/me")
        assert response.status_code == 401

    async def test_get_me_with_valid_token(self, client: AsyncClient):
        """Accessing /users/me with valid token returns user profile."""
        # Register and login
        await client.post("/auth/register", json={
            "username": "meuser",
            "email": "meuser@example.com",
            "password": "password123",
        })
        login_res = await client.post("/auth/login", json={
            "email": "meuser@example.com",
            "password": "password123",
        })
        token = login_res.json()["access_token"]

        response = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "meuser"

    async def test_health_check(self, client: AsyncClient):
        """Health check always returns 200."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
