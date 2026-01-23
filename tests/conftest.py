"""Test fixtures to stub PyQt6 GUI components for CI and headless test runs.

This file provides minimal replacements for `PyQt6.QtWidgets.QMessageBox`,
`PyQt6.QtWebEngineWidgets.QWebEngineView`, and `PyQt6.QtWebEngineCore.QWebEngineScript`
so tests don't attempt to instantiate real GUI objects that require a display.
"""
import types
import sys


class _StandardButton:
    Yes = 1
    No = 2


class _QMessageBox:
    StandardButton = _StandardButton

    @staticmethod
    def information(parent, title, text):
        return _StandardButton.Yes

    @staticmethod
    def warning(parent, title, text):
        return _StandardButton.Yes

    @staticmethod
    def critical(parent, title, text):
        return _StandardButton.Yes

    @staticmethod
    def question(parent, title, text, buttons=None):
        return _StandardButton.Yes


class _QApplication:
    _instance = None

    def __init__(self, argv=None):
        _QApplication._instance = self

    @staticmethod
    def instance():
        return _QApplication._instance

    def exec(self):
        return 0



class _QWebEngineView:
    def __init__(self, *args, **kwargs):
        self._html = ""

    def setHtml(self, html, baseUrl=None):
        self._html = html

    def setUrl(self, url):
        self._url = url

    def page(self):
        return None

    def reload(self):
        pass


class _QWebEngineScript:
    class InjectionPoint:
        DocumentReady = 0

    class ScriptWorldId:
        MainWorld = 0

    def __init__(self):
        pass

    def setInjectionPoint(self, point):
        pass

    def setWorldId(self, wid):
        pass


def _ensure_module(name: str):
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


def _install_stubs():
    # QtWidgets
    widgets = _ensure_module('PyQt6.QtWidgets')
    widgets.QMessageBox = _QMessageBox
    widgets.QApplication = _QApplication
    # Generic lightweight widget used by many UI modules
    class _DummyWidget:
        def __init__(self, *a, **k):
            pass
        def setLayout(self, *a, **k):
            pass
        def setObjectName(self, *a, **k):
            pass
        def setMaximumWidth(self, *a, **k):
            pass
        def setWindowTitle(self, *a, **k):
            pass
        def setModal(self, *a, **k):
            pass
        def resize(self, *a, **k):
            pass
        def show(self, *a, **k):
            pass
        def setText(self, *a, **k):
            pass
        def text(self, *a, **k):
            return ''

    widgets.QWidget = _DummyWidget
    widgets.QVBoxLayout = type('QVBoxLayout', (), {'setContentsMargins': lambda *a, **k: None, 'addWidget': lambda *a, **k: None, 'addStretch': lambda *a, **k: None})
    widgets.QHBoxLayout = widgets.QVBoxLayout
    widgets.QTabWidget = _DummyWidget
    widgets.QLabel = _DummyWidget
    widgets.QLineEdit = _DummyWidget
    widgets.QPushButton = _DummyWidget
    widgets.QCheckBox = _DummyWidget
    widgets.QGroupBox = _DummyWidget
    widgets.QTextEdit = _DummyWidget
    widgets.QFrame = _DummyWidget
    widgets.QDialog = _DummyWidget
    widgets.QProgressBar = _DummyWidget
    widgets.QListWidget = _DummyWidget
    widgets.QSizePolicy = type('QSizePolicy', (), {})
    widgets.QGridLayout = widgets.QVBoxLayout
    widgets.QFileDialog = type('QFileDialog', (), {'getOpenFileName': staticmethod(lambda *a, **k: ('', ''))})
    widgets.QColorDialog = type('QColorDialog', (), {'getColor': staticmethod(lambda *a, **k: None)})
    widgets.QCheckBox = _DummyWidget
    widgets.QMenu = _DummyWidget
    widgets.QInputDialog = type('QInputDialog', (), {'getText': staticmethod(lambda *a, **k: ('', True))})

    # WebEngine widgets/core
    webengine_widgets = _ensure_module('PyQt6.QtWebEngineWidgets')
    webengine_widgets.QWebEngineView = _QWebEngineView

    webengine_core = _ensure_module('PyQt6.QtWebEngineCore')
    webengine_core.QWebEngineScript = _QWebEngineScript

    # QtCore and QtGui minimal stubs used by UI modules
    core = _ensure_module('PyQt6.QtCore')
    class _Qt:
        AlignmentFlag = type('AlignmentFlag', (), {'AlignTop': 0})
    core.Qt = _Qt
    core.pyqtSignal = lambda *a, **k: type('Signal', (), {'connect': lambda *a, **k: None, 'emit': lambda *a, **k: None})
    core.QUrl = type('QUrl', (), {'__init__': lambda self, v=None: None, 'toString': lambda self: ''})
    core.QTimer = type('QTimer', (), {'start': lambda *a, **k: None})
    core.QObject = type('QObject', (), {})

    gui = _ensure_module('PyQt6.QtGui')
    gui.QFont = type('QFont', (), {})
    gui.QIcon = type('QIcon', (), {})


# Install stubs unconditionally for pytest runs to keep GUI tests headless.
_install_stubs()
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
