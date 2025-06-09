from unittest.mock import MagicMock, patch

import pytest

from codantix.config import DocStyle


class MockChatLLM:
    """
    A mock LLM for testing purposes. Mimics the interface of a real LLM but
    returns predictable responses.
    """

    def __init__(self):
        self.calls = []

    def invoke(self, messages, **kwargs):
        # Filter out unsupported parameters
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in ["model", "temperature", "max_tokens", "stream"]}

        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")

        # Echo back the input prompt
        doc = user_msg
        self.calls.append({"messages": messages, "response": doc})

        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, ChatResult

        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(content=doc),
                    generation_info={"model": filtered_kwargs.get("model", "gpt-4")},
                )
            ]
        )

    def generate(self, messages, stop=None, callbacks=None, **kwargs):
        # Filter out unsupported parameters
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in ["model", "temperature", "max_tokens", "stream"]}

        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, ChatResult

        user_msg = next((m.content for m in messages if m.type == "human"), "")

        # Echo back the input prompt
        doc = user_msg
        model = filtered_kwargs.get("model", "gpt-4")

        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(content=doc),
                    generation_info={"model": model},
                )
            ]
        )


@pytest.fixture(autouse=True)
def mock_llm():
    llm = MockChatLLM()
    return llm


@pytest.fixture(autouse=True)
def patch_llm(monkeypatch):
    """Patch the LLM initialization to use our mock implementation."""

    def mock_init_llm(*args, **kwargs):
        llm = MockChatLLM()
        return llm

    def mock_generate(self, messages, stop=None, callbacks=None, **kwargs):
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, ChatResult

        # Create a mock LLM instance to generate the response
        mock_llm = MockChatLLM()
        user_msg = next((m.content for m in messages if m.type == "human"), "")
        import re

        m = re.search(r"for a (\w+) named '([^']+)'", user_msg)
        elem_type = m.group(1).lower() if m else "element"
        elem_name = m.group(2) if m else "unknown"

        doc = mock_llm._generate_docstring(elem_type, elem_name)

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=doc))])

    # Patch both the old and new import paths
    monkeypatch.setattr("langchain.chat_models.init_chat_model", mock_init_llm)
    monkeypatch.setattr("langchain_openai.chat_models.ChatOpenAI._generate", mock_generate)


@pytest.fixture(autouse=True)
def patch_openai_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-key")


@pytest.fixture(autouse=True)
def mock_embedding_model():
    """Mock the embedding model to prevent downloading during tests."""
    with patch("langchain_openai.OpenAIEmbeddings") as mock_embeddings:
        mock_instance = MagicMock()
        mock_instance.embed_query.return_value = [0.1] * 1536
        mock_instance.embed_documents.side_effect = lambda texts: [[0.1] * 1536 for _ in texts]
        mock_embeddings.return_value = mock_instance
        yield mock_embeddings
