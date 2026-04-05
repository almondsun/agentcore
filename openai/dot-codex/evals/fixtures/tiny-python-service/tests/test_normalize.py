from tiny_service.normalize import normalize_user_id


def test_normalize_user_id_strips_and_lowercases() -> None:
    assert normalize_user_id(" Alice ") == "alice"


def test_normalize_user_id_blank_input_returns_empty_string() -> None:
    assert normalize_user_id("   ") == ""
