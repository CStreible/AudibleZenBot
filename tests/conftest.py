import pytest
import sys

# Remember the original core.http_session module (if any) so we can restore
# it before each test. Many tests monkeypatch `sys.modules['core.http_session']`
# and rely on `importlib.reload(core.twitch_emotes)` to pick up the stub. When
# running tests in the same worker process (xdist), leftover sys.modules
# entries can leak between tests and cause surprising real-network calls.
_ORIGINAL_CORE_HTTP_SESSION = sys.modules.get('core.http_session', None)


@pytest.fixture(autouse=True)
def reset_twitch_emote_manager():
    # Restore the original http_session module before test starts
    try:
        if _ORIGINAL_CORE_HTTP_SESSION is None:
            if 'core.http_session' in sys.modules:
                del sys.modules['core.http_session']
        else:
            sys.modules['core.http_session'] = _ORIGINAL_CORE_HTTP_SESSION
    except Exception:
        pass

    # Reset any module-level manager state so tests get a fresh manager
    try:
        from core.twitch_emotes import reset_manager
        reset_manager()
    except Exception:
        pass

    yield

    # After the test, restore the original http_session again to avoid
    # leaving test-specific stubs in place for the next test.
    try:
        if _ORIGINAL_CORE_HTTP_SESSION is None:
            if 'core.http_session' in sys.modules:
                del sys.modules['core.http_session']
        else:
            sys.modules['core.http_session'] = _ORIGINAL_CORE_HTTP_SESSION
    except Exception:
        pass

    try:
        from core.twitch_emotes import reset_manager
        reset_manager()
    except Exception:
        pass
