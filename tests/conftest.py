import pytest
import sys

# --- Qt headless shim: ensure WebEngine has flags and QApplication gets non-empty argv ---
import os
try:
    os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--no-sandbox --disable-gpu --headless --disable-software-rasterizer --enable-logging=stderr --v=1')
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    # If PyQt6 is present, ensure QApplication will not be constructed with an empty argv
    try:
        from PyQt6.QtWidgets import QApplication as _RealQApp

        class _QAppWrapper(_RealQApp):
            def __init__(self, argv=None):
                if argv is None or len(argv) == 0:
                    argv = [sys.argv[0] or 'pytest']
                super().__init__(argv)

        import PyQt6.QtWidgets as _qtwidgets
        _qtwidgets.QApplication = _QAppWrapper
    except Exception:
        # PyQt6 not available or replacement failed; ignore
        pass
except Exception:
    pass
# --- end Qt shim ---

# Remember the original core.http_session module (if any) so we can restore
# it before each test. Many tests monkeypatch `sys.modules['core.http_session']`
# and rely on `importlib.reload(core.twitch_emotes)` to pick up the stub. When
# running tests in the same worker process (xdist), leftover sys.modules
# entries can leak between tests and cause surprising real-network calls.
_ORIGINAL_CORE_HTTP_SESSION = sys.modules.get('core.http_session', None)


@pytest.fixture(autouse=True)
def reset_twitch_emote_manager():
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
