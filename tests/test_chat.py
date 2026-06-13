"""
tests/test_chat.py
------------------
Tests for chat creation and message history endpoints.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


async def register_and_login(client: AsyncClient, username: str, email: str) -> str:
    """Helper: register a user and return their access token."""
    await client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "password123",
    })
    res = await client.post("/auth/login", json={
        "email": email,
        "password": "password123",
    })
    return res.json()["access_token"]


class TestChats:

    async def test_create_private_chat(self, client: AsyncClient):
        """Two users can create a private chat."""
        token_a = await register_and_login(client, "chat_user_a", "chat_a@example.com")
        token_b = await register_and_login(client, "chat_user_b", "chat_b@example.com")

        # Get user B's ID
        me_res = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        user_b_id = me_res.json()["id"]

        # User A creates a chat with User B
        res = await client.post(
            "/chats/",
            json={"other_user_id": user_b_id},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res.status_code == 200
        chat = res.json()
        assert chat["type"] == "private"
        assert "id" in chat

    async def test_create_chat_idempotent(self, client: AsyncClient):
        """Creating a chat between same users twice returns same chat."""
        token_a = await register_and_login(client, "idem_a", "idem_a@example.com")
        token_b = await register_and_login(client, "idem_b", "idem_b@example.com")

        me_res = await client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        user_b_id = me_res.json()["id"]

        res1 = await client.post(
            "/chats/",
            json={"other_user_id": user_b_id},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        res2 = await client.post(
            "/chats/",
            json={"other_user_id": user_b_id},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert res1.json()["id"] == res2.json()["id"]

    async def test_list_my_chats(self, client: AsyncClient):
        """User can list their chats."""
        token = await register_and_login(client, "lister", "lister@example.com")
        res = await client.get(
            "/chats/",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    async def test_create_group(self, client: AsyncClient):
        """A user can create a group chat."""
        token = await register_and_login(client, "group_admin", "gadmin@example.com")
        res = await client.post(
            "/groups/",
            json={"name": "Test Group", "description": "A test group", "member_ids": []},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Test Group"
        assert "id" in data
        assert "chat_id" in data

    async def test_message_history_requires_auth(self, client: AsyncClient):
        """Message history endpoint requires authentication."""
        res = await client.get("/chats/00000000-0000-0000-0000-000000000000/messages")
        assert res.status_code == 401
