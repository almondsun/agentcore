from tiny_easy.validation import parse_retry_delay


def test_parse_retry_delay_accepts_integer_input() -> None:
    assert parse_retry_delay(5) == 5


def test_parse_retry_delay_accepts_trimmed_string_input() -> None:
    assert parse_retry_delay(" 12 ") == 12


def test_parse_retry_delay_rejects_negative_values() -> None:
    try:
        parse_retry_delay("-1")
    except ValueError as exc:
        assert "zero or greater" in str(exc)
    else:
        raise AssertionError("Expected ValueError for negative retry delay")
