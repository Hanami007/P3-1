import pytest

from app.services import llm


class _FakeResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


@pytest.fixture()
def gemini_provider(monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_provider", "gemini")
    monkeypatch.setattr(llm.settings, "gemini_api_key", "fake-key")


def test_gemini_retries_on_503_then_succeeds(monkeypatch, gemini_provider):
    calls = []

    def fake_post(url, params=None, json=None, timeout=None):
        calls.append(1)
        if len(calls) < 2:
            return _FakeResponse(503, text="overloaded")
        return _FakeResponse(200, json_data={"candidates": [{"content": {"parts": [{"text": "hello"}]}}]})

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    monkeypatch.setattr(llm.time, "sleep", lambda _: None)

    result = llm.ask("hi")
    assert result == "hello"
    assert len(calls) == 2


def test_gemini_does_not_retry_non_retryable_status(monkeypatch, gemini_provider):
    calls = []

    def fake_post(url, params=None, json=None, timeout=None):
        calls.append(1)
        return _FakeResponse(429, text="quota exceeded")

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    monkeypatch.setattr(llm.time, "sleep", lambda _: None)

    with pytest.raises(llm.LLMError, match="429"):
        llm.ask("hi")
    assert len(calls) == 1


def test_gemini_gives_up_after_max_attempts_of_503(monkeypatch, gemini_provider):
    calls = []

    def fake_post(url, params=None, json=None, timeout=None):
        calls.append(1)
        return _FakeResponse(503, text="overloaded")

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    monkeypatch.setattr(llm.time, "sleep", lambda _: None)

    with pytest.raises(llm.LLMError, match="503"):
        llm.ask("hi")
    assert len(calls) == llm._MAX_ATTEMPTS
