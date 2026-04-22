from trashdig.agents.utils.json_utils import extract_json_list, parse_json_response


def test_parse_json_response_direct():
    text = '{"key": "value"}'
    assert parse_json_response(text) == {"key": "value"}

def test_parse_json_response_markdown():
    text = "```json\n{\"key\": \"value\"}\n```"
    assert parse_json_response(text) == {"key": "value"}

    text = "```\n{\"key\": \"value\"}\n```"
    assert parse_json_response(text) == {"key": "value"}

def test_parse_json_response_embedded():
    text = "Here is the data: {\"key\": \"value\"} hope it helps!"
    assert parse_json_response(text) == {"key": "value"}

def test_parse_json_response_list_embedded():
    text = "Items: [1, 2, 3]"
    # Currently parse_json_response expects { and }
    # Let's see how it handles it
    assert parse_json_response(text) == {}

def test_parse_json_response_invalid():
    assert parse_json_response("not json") == {}
    assert parse_json_response("") == {}

def test_extract_json_list():
    text = '{"findings": [{"id": 1}, {"id": 2}]}'
    assert extract_json_list(text, "findings") == [{"id": 1}, {"id": 2}]

    text = '{"findings": {"id": 1}}'
    assert extract_json_list(text, "findings") == [{"id": 1}]

    text = '{"other": 1}'
    assert extract_json_list(text, "findings") == []
