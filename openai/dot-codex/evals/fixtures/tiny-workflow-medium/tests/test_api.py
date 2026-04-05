from tiny_medium.api import summarize_user


def test_summarize_user_normalizes_id_and_status() -> None:
    assert summarize_user(" Alice ", "enabled") == {
        "id": "alice",
        "status": "active",
    }
