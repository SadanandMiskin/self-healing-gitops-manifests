from agent.diagnoser import _parse_llm_response


def test_parse_json_fenced_llm_response() -> None:
    text = """
```json
{
  "category": "missing_env_var",
  "confidence": 1.0,
  "explanation": "REQUIRED_GREETING is missing.",
  "recommended_fix": "Add env var."
}
```
"""

    issue_type, confidence, recommended_fix = _parse_llm_response(text)

    assert issue_type == "missing_env_var"
    assert confidence == 1.0
    assert recommended_fix == "Add env var."


def test_parse_unknown_json_response() -> None:
    text = '{"category": "unknown", "confidence": 0.1, "fix": "Investigate."}'

    issue_type, confidence, recommended_fix = _parse_llm_response(text)

    assert issue_type == "unknown"
    assert confidence == 0.1
    assert recommended_fix == "Investigate."
