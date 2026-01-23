import importlib
import types
import sys

UI_MODULES = [
    ('ui.settings_page', 'SettingsPage'),
    ('ui.connections_page', 'OAuthBrowserDialog'),
]


def _inject_minimal_pyqt():
    # Create minimal PyQt6 stub modules to allow imports in headless tests
    pyqt = types.ModuleType('PyQt6')
    qtwidgets = types.ModuleType('PyQt6.QtWidgets')
    qtcore = types.ModuleType('PyQt6.QtCore')
    qtgui = types.ModuleType('PyQt6.QtGui')
    webengine = types.ModuleType('PyQt6.QtWebEngineWidgets')

    # Minimal classes/attributes used by UI modules
    class Dummy:
        def __init__(self, *a, **k):
            pass

    setattr(qtwidgets, 'QWidget', Dummy)
    setattr(qtwidgets, 'QDialog', Dummy)
    setattr(qtwidgets, 'QLabel', Dummy)
    setattr(qtwidgets, 'QVBoxLayout', Dummy)
    setattr(qtwidgets, 'QProgressBar', Dummy)
    setattr(qtwidgets, 'QWebEngineView', Dummy)

    setattr(qtcore, 'Qt', object)
    def _pyqtSignal(*a, **k):
        class _S:
            def connect(self, *a, **k):
                return None
            def emit(self, *a, **k):
                return None
        return _S()
    setattr(qtcore, 'pyqtSignal', _pyqtSignal)
    setattr(qtcore, 'QUrl', object)

    setattr(qtgui, 'QFont', object)

    sys.modules['PyQt6'] = pyqt
    sys.modules['PyQt6.QtWidgets'] = qtwidgets
    sys.modules['PyQt6.QtCore'] = qtcore
    sys.modules['PyQt6.QtGui'] = qtgui
    sys.modules['PyQt6.QtWebEngineWidgets'] = webengine


def test_ui_modules_importable(monkeypatch):
    # Inject minimal PyQt before importing UI modules
    _inject_minimal_pyqt()

    for module_name, symbol in UI_MODULES:
        mod = importlib.import_module(module_name)
        importlib.reload(mod)
        assert hasattr(mod, '__name__')
        assert hasattr(mod, symbol)
