from trashdig.agents.utils.json_utils import (
    classify_llm_failure,
    extract_json_list,
    parse_json_response,
)


def test_parse_json_response_direct():
    text = '{"key": "value"}'
    assert parse_json_response(text) == {"key": "value"}


def test_parse_json_response_markdown():
    text = '```json\n{"key": "value"}\n```'
    assert parse_json_response(text) == {"key": "value"}

    text = '```\n{"key": "value"}\n```'
    assert parse_json_response(text) == {"key": "value"}


def test_parse_json_response_embedded():
    text = 'Here is the data: {"key": "value"} hope it helps!'
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


def test_classify_llm_failure_api_error():
    diagnostics = {"error_code": "500", "error_message": "internal error"}
    assert classify_llm_failure("", diagnostics) == "api_error:500"


def test_classify_llm_failure_prompt_blocked():
    # ADK's LlmResponse.create() maps GenerateContentResponse.prompt_feedback
    # .block_reason into `error_code` when the API returns zero candidates —
    # i.e. the prompt itself was blocked before any generation happened.
    diagnostics = {"error_code": "SAFETY", "error_message": "blocked by safety filter"}
    assert classify_llm_failure("", diagnostics) == "prompt_blocked:SAFETY"

    diagnostics = {"error_code": "PROHIBITED_CONTENT"}
    assert classify_llm_failure("", diagnostics) == "prompt_blocked:PROHIBITED_CONTENT"


def test_classify_llm_failure_safety_block():
    diagnostics = {"finish_reason": "SAFETY"}
    assert classify_llm_failure("", diagnostics) == "safety_block:SAFETY"

    diagnostics = {"finish_reason": "PROHIBITED_CONTENT"}
    assert classify_llm_failure("some text", diagnostics) == "safety_block:PROHIBITED_CONTENT"


def test_classify_llm_failure_empty_response():
    assert classify_llm_failure("", {}) == "empty_response"
    assert classify_llm_failure("   ", {}) == "empty_response"


def test_classify_llm_failure_model_refusal():
    assert classify_llm_failure("Sorry, I cannot fulfill this request.", {}) == "model_refusal"
    assert classify_llm_failure("I'm unable to help with that.", {}) == "model_refusal"
    assert (
        classify_llm_failure("I can't assist with analyzing this codebase.", {}) == "model_refusal"
    )


def test_classify_llm_failure_malformed_json():
    assert classify_llm_failure("this is just plain prose, not JSON", {}) == "malformed_json"
    assert classify_llm_failure("this is just plain prose, not JSON", None) == "malformed_json"
