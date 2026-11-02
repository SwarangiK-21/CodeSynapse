import json
from types import SimpleNamespace
import pytest
from google.genai import errors
from codesynapse import config
from codesynapse.services import chat, coach

class FakeModels:
    def __init__(self, behaviour):
        self.behaviour, self.calls = behaviour, []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        result = self.behaviour(model)
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(text=result)

def use(monkeypatch, behaviour):
    models = FakeModels(behaviour)
    monkeypatch.setattr(coach, "client", SimpleNamespace(models=models))
    monkeypatch.setattr(config, "GEMINI_MODELS", ["first", "second"])
    return models

def api_error(code):
    return errors.ClientError(code, {"error": {"code": code, "message": "m", "status": "S"}})

def advice(raw):
    return json.loads(raw)["advice"]

def test_missing_key(monkeypatch):
    monkeypatch.setattr(coach, "client", None)
    assert "Key Missing" in advice(coach.ask_gemini("q", []))

@pytest.mark.parametrize("code,text,attempts", [
    (400, "key was rejected", 1), (403, "key was rejected", 1),
    (404, "models exist", 2), (429, "Quota", 2),
])
def test_each_failure_gets_an_accurate_message(monkeypatch, code, text, attempts):
    models = use(monkeypatch, lambda m: api_error(code))
    assert text in advice(coach.ask_gemini("q", []))
    assert len(models.calls) == attempts

def test_falls_back_to_next_model(monkeypatch):
    models = use(monkeypatch, lambda m: api_error(429) if m == "first" else '{"advice": "ok", "actions": []}')
    assert advice(coach.ask_gemini("q", [])) == "ok"
    assert models.calls == ["first", "second"]

def test_prompt_includes_stats_and_history():
    prompt = coach.build_prompt("next?", [{"platform": "GitHub"}], [{"role": "user", "content": "hello"}])
    assert "GitHub" in prompt and "user: hello" in prompt and "next?" in prompt

def test_prompt_says_when_there_are_no_stats():
    assert "not synced" in coach.build_prompt("q", [], [])

@pytest.mark.parametrize("raw", ['{"advice": "Try', '{"advice": "x", "actions": [{"task": "y"}]}', "[1, 2]"])
def test_unreadable_replies_are_hidden(raw):
    assert "unreadable" in chat.format_reply(raw)

def test_reply_without_actions():
    assert chat.format_reply('{"advice": "Rest", "actions": []}') == "Rest"
