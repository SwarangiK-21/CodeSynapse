from types import SimpleNamespace
import httpx
import pytest
from google.genai import errors
from pydantic import BaseModel
from codesynapse import config
from codesynapse.services import coach, llm

class Reply(BaseModel):
    answer: str

GOOD = '{"answer": "yes"}'

def api_error(code):
    kind = errors.ClientError if code < 500 else errors.ServerError
    return kind(code, {"error": {"code": code, "message": "m", "status": "S"}})

@pytest.fixture
def setup(monkeypatch):
    """Replays scripted outcomes and records calls and waits."""
    state = SimpleNamespace(calls=[], waits=[], script=[])
    def generate_content(model, contents, config):
        state.calls.append(model)
        result = state.script.pop(0)
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(text=result, usage_metadata=SimpleNamespace(prompt_token_count=5, candidates_token_count=2))
    monkeypatch.setattr(coach, "client", SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    monkeypatch.setattr(config, "GEMINI_MODELS", ["first", "second"])
    monkeypatch.setattr(llm.time, "sleep", state.waits.append)
    return state

def test_counts_tokens(setup):
    setup.script = [GOOD]
    usage = llm.Usage()
    assert llm.generate_json("p", Reply, usage).answer == "yes"
    assert (usage.calls, usage.prompt_tokens, usage.output_tokens) == (1, 5, 2)

def test_overload_moves_to_next_model_without_waiting(setup):
    setup.script = [api_error(503), GOOD]
    assert llm.generate_json("p", Reply).answer == "yes"
    assert setup.calls == ["first", "second"] and setup.waits == []

def test_waits_when_every_model_is_overloaded(setup):
    setup.script = [api_error(503), api_error(504), GOOD]
    assert llm.generate_json("p", Reply).answer == "yes"
    assert setup.waits == [llm.BACKOFF_SECONDS]

def test_timeouts_are_retried(setup):
    setup.script = [httpx.ReadTimeout("slow"), GOOD]
    assert llm.generate_json("p", Reply).answer == "yes"

def test_dropped_connections_are_retried(setup):
    setup.script = [ConnectionResetError("reset"), httpx.ConnectError("down"), GOOD]
    assert llm.generate_json("p", Reply).answer == "yes"

def test_gives_up_after_every_round(setup):
    setup.script = [api_error(503)] * 6
    with pytest.raises(llm.LLMError):
        llm.generate_json("p", Reply)
    assert len(setup.calls) == 6 and len(setup.waits) == llm.ROUNDS - 1

def test_rejected_key_stops_immediately(setup):
    setup.script = [api_error(403)]
    with pytest.raises(llm.LLMError, match="key was rejected"):
        llm.generate_json("p", Reply)
    assert len(setup.calls) == 1

def test_malformed_reply_tries_next_model(setup):
    setup.script = ["not json", GOOD]
    assert llm.generate_json("p", Reply).answer == "yes"

def test_empty_reply_tries_next_model(setup):
    setup.script = [None, GOOD]
    assert llm.generate_json("p", Reply).answer == "yes"
