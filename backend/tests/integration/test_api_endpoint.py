"""Integration tests for /chat endpoint."""
import pytest


def test_chat_basic(client):
    """Test basic chat request."""
    response = client.post(
        "/chat",
        json={"message": "Tell me about the Noor Collection"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert isinstance(data["reply"], str)
    assert len(data["reply"]) > 0


def test_chat_with_context(client):
    """Test chat request with conversation context."""
    response = client.post(
        "/chat",
        json={
            "message": "What about the second one?",
            "context": [
                {"role": "user", "content": "Show me pieces from the Velvet Line"},
                {"role": "assistant", "content": "The Velvet Line features several handcrafted pieces..."},
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "reply" in data


def test_chat_empty_message(client):
    """Test that empty message returns 400."""
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 400


def test_chat_whitespace_message(client):
    """Test that whitespace-only message returns 400."""
    response = client.post("/chat", json={"message": "   "})
    assert response.status_code == 400


def test_chat_malformed_json(client):
    """Test that malformed JSON returns 422."""
    response = client.post(
        "/chat",
        json={"invalid_field": "test"},
    )
    assert response.status_code == 422


def test_health_check(client):
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
