from box_doc_summarizer.intent import classify_intent, parse_folder_id
from box_doc_summarizer.llm import harness_env_available, parse_json_object, resolve_llm_env


def test_folder_parsing():
    assert parse_folder_id("Summarize folder 123456789") == "123456789"
    assert parse_folder_id("https://app.box.com/folder/987654321") == "987654321"
    assert parse_folder_id("hi") == ""


def test_intents():
    assert classify_intent("hi") == "chat"
    assert classify_intent("help") == "help"
    assert classify_intent("Summarize folder 123456") == "summarize"
    assert classify_intent("refresh") == "summarize"


def test_llm_env_prefers_harness(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "o")
    monkeypatch.setenv("HARNESS_INFERENCE_API_KEY", "h")
    monkeypatch.setenv("HARNESS_INFERENCE_MODEL", "m")
    env = resolve_llm_env()
    assert env["api_key"] == "h" and env["model"] == "m"
    assert harness_env_available()
    monkeypatch.setenv("BOX_SUMMARIZER_LLM", "0")
    assert not harness_env_available()


def test_parse_json_object():
    assert parse_json_object('```json\n{"brief": "x"}\n```') == {"brief": "x"}
    assert parse_json_object("nope") is None
