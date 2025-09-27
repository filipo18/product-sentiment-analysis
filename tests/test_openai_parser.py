import pytest

from app.utils.openai_parser import OpenAIParseError, parse_sentiment_payload, parse_summary_payload


def test_parse_sentiment_payload_valid():
    payload = {"sentiment": "positive", "confidence": 0.9, "aspects": {"battery": "positive"}}
    result = parse_sentiment_payload(payload)
    assert result["sentiment"] == "positive"
    assert result["confidence"] == 0.9
    assert result["aspects"] == {"battery": "positive"}


def test_parse_sentiment_payload_invalid_sentiment():
    with pytest.raises(OpenAIParseError):
        parse_sentiment_payload({"sentiment": "great", "confidence": 0.5})


def test_parse_summary_payload_truncates_lists():
    payload = {
        "overall": "Great",
        "delights": [str(i) for i in range(10)],
        "pain_points": [str(i) for i in range(10)],
    }
    result = parse_summary_payload(payload)
    assert len(result["delights"]) == 5
    assert len(result["pain_points"]) == 5
