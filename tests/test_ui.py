import gradio as gr
import pytest
from codesynapse.db.session import SessionLocal
from codesynapse.services import chat, users
from codesynapse.ui import app as ui

def new_token():
    with SessionLocal() as db:
        return users.create_user(db)[1]

def test_first_visit_creates_a_user():
    token, github, leetcode, stats_text, chart, history = ui.load_session(None)
    with SessionLocal() as db:
        assert users.get_user_by_token(db, token)
    assert (github, leetcode, chart, history) == ("", "", None, [])
    assert "Sync your profiles" in stats_text

def test_returning_visit_restores_data(fake_stats, fake_ai):
    token = new_token()
    ui.fetch_data_logic(token, "octocat", "")
    ui.chat_logic("hello", [], token)

    same_token, github, _, stats_text, chart, history = ui.load_session(token)
    assert same_token == token and github == "octocat"
    assert "GitHub" in stats_text and chart is not None
    assert history[0] == {"role": "user", "content": "hello"}

def test_unknown_token_cannot_read_data(fake_stats):
    with pytest.raises(gr.Error):
        ui.fetch_data_logic("made-up", "octocat", "")

def test_invalid_username_shows_an_error():
    with pytest.raises(gr.Error):
        ui.fetch_data_logic(new_token(), "../etc", "")

def test_pdf_needs_stats():
    assert ui.generate_pdf_logic(new_token()) is None

def test_pdf_files_are_unique(fake_stats):
    token = new_token()
    ui.fetch_data_logic(token, "octocat", "")
    assert ui.generate_pdf_logic(token) != ui.generate_pdf_logic(token)

def test_chat_uses_only_this_users_history(fake_ai):
    alice, bob = new_token(), new_token()
    ui.chat_logic("alice note", [], alice)
    ui.chat_logic("bob note", [], bob)
    with SessionLocal() as db:
        history = chat.get_history(db, users.get_user_by_token(db, bob))
    assert "alice note" not in str(history)

def test_chart_skips_platforms_without_data():
    assert ui.build_chart([{"platform": "GitHub", "stats": {}, "score_norm": None}]) is None
