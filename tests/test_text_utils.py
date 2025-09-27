from app.utils.text import chunked, normalize_text


def test_normalize_text_removes_urls_and_lowercases():
    text = "Check https://example.com THIS"
    assert normalize_text(text) == "check this"


def test_chunked_breaks_iterable():
    items = list(chunked(range(5), 2))
    assert items == [[0, 1], [2, 3], [4]]


def test_chunked_invalid_size():
    try:
        list(chunked([1], 0))
    except ValueError as exc:
        assert "size must be positive" in str(exc)
    else:
        assert False, "Expected ValueError"
