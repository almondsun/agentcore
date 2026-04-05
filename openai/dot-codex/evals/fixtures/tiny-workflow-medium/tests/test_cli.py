from tiny_medium.cli import format_summary_line


def test_format_summary_line_uses_trimmed_values() -> None:
    assert format_summary_line(" Alice ", " enabled ") == "alice:enabled"
