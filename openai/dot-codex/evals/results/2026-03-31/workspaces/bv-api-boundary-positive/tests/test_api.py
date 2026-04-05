from tiny_service.api import lookup_user


def test_lookup_user_normalizes_case_and_space() -> None:
    assert lookup_user(" Alice ") == "user:alice"
