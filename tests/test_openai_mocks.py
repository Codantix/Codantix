"""
Tests for OpenAI API mocks using responses library.
"""

import json
import os
import random
from typing import Any, Dict, List

import pytest
import responses

# Mock OpenAI API endpoints
OPENAI_COMPLETION_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_EMBEDDING_URL = "https://api.openai.com/v1/embeddings"


def generate_random_embedding(dimensions: int) -> List[float]:
    """Generate a random embedding vector of specified dimensions."""
    return [random.uniform(-1, 1) for _ in range(dimensions)]


@pytest.fixture
def mock_openai_completion():
    """Mock OpenAI completion API endpoint."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:

        def completion_callback(request):
            # Parse the request body
            body = json.loads(request.body)
            messages = body.get("messages", [])

            # Extract the user message
            user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")

            # Create a response that reflects the input
            response = {
                "id": "mock-completion-id",
                "object": "chat.completion",
                "created": 1234567890,
                "model": "gpt-4",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": f"Mock response to: {user_msg}",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": len(user_msg.split()),
                    "completion_tokens": 10,
                    "total_tokens": len(user_msg.split()) + 10,
                },
            }
            return (200, {}, json.dumps(response))

        rsps.add_callback(
            responses.POST,
            OPENAI_COMPLETION_URL,
            callback=completion_callback,
            content_type="application/json",
        )
        yield rsps


@pytest.fixture
def mock_openai_embedding():
    """Mock OpenAI embedding API endpoint."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:

        def embedding_callback(request):
            # Parse the request body
            body = json.loads(request.body)
            input_text = body.get("input", "")
            model = body.get("model", "text-embedding-ada-002")

            # Generate random embeddings based on model
            dimensions = 1536 if "ada" in model else 1024
            embeddings = [
                generate_random_embedding(dimensions)
                for _ in range(len(input_text) if isinstance(input_text, list) else 1)
            ]

            response = {
                "object": "list",
                "data": [
                    {"object": "embedding", "embedding": embedding, "index": i}
                    for i, embedding in enumerate(embeddings)
                ],
                "model": model,
                "usage": {
                    "prompt_tokens": (
                        len(input_text.split())
                        if isinstance(input_text, str)
                        else sum(len(t.split()) for t in input_text)
                    ),
                    "total_tokens": (
                        len(input_text.split())
                        if isinstance(input_text, str)
                        else sum(len(t.split()) for t in input_text)
                    ),
                },
            }
            return (200, {}, json.dumps(response))

        rsps.add_callback(
            responses.POST,
            OPENAI_EMBEDDING_URL,
            callback=embedding_callback,
            content_type="application/json",
        )
        yield rsps


def test_openai_completion_mock(mock_openai_completion):
    """Test the OpenAI completion mock."""
    import requests

    # Test data
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    # Make request to mocked endpoint
    response = requests.post(
        OPENAI_COMPLETION_URL,
        headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', 'dummy-key')}"},
        json={"model": "gpt-4", "messages": messages, "temperature": 0.7},
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert "message" in data["choices"][0]
    assert "content" in data["choices"][0]["message"]
    assert (
        "Mock response to: Hello, how are you?"
        in data["choices"][0]["message"]["content"]
    )


def test_openai_embedding_mock(mock_openai_embedding):
    """Test the OpenAI embedding mock."""
    import requests

    # Test data
    input_text = "This is a test sentence."

    # Make request to mocked endpoint
    response = requests.post(
        OPENAI_EMBEDDING_URL,
        headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', 'dummy-key')}"},
        json={"model": "text-embedding-ada-002", "input": input_text},
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 1
    assert "embedding" in data["data"][0]
    assert len(data["data"][0]["embedding"]) == 1536  # ada-002 dimensions

    # Test batch embedding
    batch_text = ["First sentence.", "Second sentence."]
    response = requests.post(
        OPENAI_EMBEDDING_URL,
        headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY', 'dummy-key')}"},
        json={"model": "text-embedding-3-large", "input": batch_text},
    )

    # Verify batch response
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 2
    assert all("embedding" in item for item in data["data"])
    assert all(
        len(item["embedding"]) == 1024 for item in data["data"]
    )  # text-embedding-3-large dimensions
