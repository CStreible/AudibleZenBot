import pytest

# Ensure core.twitch_emotes manager is reset between tests to avoid
# cross-test shared-state when tests monkeypatch `core.http_session`.

@pytest.fixture(autouse=True)
def reset_twitch_emote_manager():
    try:
        from core.twitch_emotes import reset_manager
        reset_manager()
    except Exception:
        pass
    yield
    try:
        from core.twitch_emotes import reset_manager
        reset_manager()
    except Exception:
        pass
