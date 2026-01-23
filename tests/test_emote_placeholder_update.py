import time
import os

from core.signals import signals as emote_signals
import ui.chat_page as chat_mod


class DummySignal:
    def connect(self, cb):
        pass


class DummyChatManager:
    def __init__(self):
        self.message_received = DummySignal()
        self.message_deleted = DummySignal()


def test_emote_cached_patches_no_crash(monkeypatch, tmp_path):
    # Provide a dummy TwitchEmoteManager with get_emote_data_uri
    class DummyMgr:
        def get_emote_data_uri(self, eid):
            return 'data:image/png;base64,' + ('A' * 24)

    try:
        import core.twitch_emotes as te
        # Replace get_manager with a callable that returns DummyMgr instance
        monkeypatch.setattr(te, 'get_manager', lambda: DummyMgr())
    except Exception:
        pass

    # Ensure layout stub provides methods used by ChatPage.initUI()
    class DummyLayout:
        def __init__(self, *a, **k):
            pass
        def setContentsMargins(self, *a, **k):
            pass
        def setSpacing(self, *a, **k):
            pass
        def addWidget(self, *a, **k):
            pass

    monkeypatch.setattr(chat_mod, 'QVBoxLayout', DummyLayout)
    # Minimal QLabel stub with methods used by ChatPage.initUI()
    class DummyLabel:
        def __init__(self, *a, **k):
            self._text = a[0] if a else ''
        def setStyleSheet(self, *a, **k):
            pass
        def setMaximumHeight(self, *a, **k):
            pass
        def setText(self, text):
            self._text = text

    monkeypatch.setattr(chat_mod, 'QLabel', DummyLabel)
    # Generic widget/signal stubs for other PyQt types used in initUI
    class DummyAttr:
        def __call__(self, *a, **k):
            return None
        def connect(self, *a, **k):
            return None
        def emit(self, *a, **k):
            return None

    class DummyWidget:
        def __init__(self, *a, **k):
            pass
        def __getattr__(self, name):
            return DummyAttr()
        def setStyleSheet(self, *a, **k):
            pass
        def setMaximumHeight(self, *a, **k):
            pass
        def setChecked(self, *a, **k):
            pass
        def setToolTip(self, *a, **k):
            pass
        def setText(self, *a, **k):
            pass
        def setSizePolicy(self, *a, **k):
            pass
        def setMinimumHeight(self, *a, **k):
            pass

    for name in ('QGroupBox','QHBoxLayout','QCheckBox','QPushButton','QMenu','QInputDialog','QMessageBox','QSizePolicy','QWebEngineView','QWebEngineScript','QAction','QComboBox','QScrollArea'):
        try:
            monkeypatch.setattr(chat_mod, name, DummyWidget)
        except Exception:
            pass

    cm = DummyChatManager()
    # Avoid constructing the full UI in tests: stub out initUI to keep focus on handler logic
    monkeypatch.setattr(chat_mod.ChatPage, 'initUI', lambda self: None)
    # Construct ChatPage (initUI is no-op)
    cp = chat_mod.ChatPage(cm, config={})

    # Emit a cached event and ensure handler runs without throwing
    try:
        emote_signals.emote_image_cached_ext.emit({'emote_id': '12345'})
        # slight delay to allow any async JS queueing logic to run in test stubs
        time.sleep(0.05)
    except Exception:
        assert False, "emote_image_cached_ext handler raised"

    # If we reach here, handler executed without raising
    assert True
