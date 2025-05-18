import pytest

class MockChatLLM:
    """
    A mock LLM for testing purposes. Mimics the interface of a real LLM but returns predictable responses.
    """
    def __init__(self, doc_style='google'):
        self.doc_style = doc_style
        self.calls = []

    def invoke(self, messages):
        user_msg = next((m['content'] for m in messages if m['role'] == 'user'), '')
        import re
        m = re.search(r"for a (\w+) named '([^']+)'", user_msg)
        elem_type = m.group(1).lower() if m else 'element'
        elem_name = m.group(2) if m else 'unknown'
        if self.doc_style == 'google':
            doc = f'"""Google docstring for {elem_type} {elem_name}"""'
        elif self.doc_style == 'numpy':
            doc = f'"""NumPy docstring for {elem_type} {elem_name}"""'
        elif self.doc_style == 'jsdoc':
            doc = f'/** JSDoc for {elem_type} {elem_name} */'
        else:
            doc = f'Docstring for {elem_type} {elem_name}'
        self.calls.append({'messages': messages, 'response': doc})
        return {"content": doc}

@pytest.fixture(autouse=True)
def patch_llm(monkeypatch):
    def mock_init_llm(self):
        doc_style = getattr(self, 'doc_style', 'google')
        if hasattr(doc_style, 'value'):
            doc_style = doc_style.value
        return MockChatLLM(doc_style)
    monkeypatch.setattr("codantix.doc_generator.DocumentationGenerator._init_llm", mock_init_llm) 