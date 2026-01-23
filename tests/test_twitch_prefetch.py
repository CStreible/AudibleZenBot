import unittest
from unittest.mock import Mock
import sys
import types
from unittest.mock import Mock

# Stub out core.http_session.make_retry_session before importing module under test
if 'core.http_session' not in sys.modules:
    mod = types.ModuleType('core.http_session')
    def _make_retry_session():
        return Mock()
    mod.make_retry_session = _make_retry_session
    sys.modules['core.http_session'] = mod

# Stub PyQt6.QtCore if not available so tests don't require PyQt6
if 'PyQt6' not in sys.modules:
    pyqt6 = types.ModuleType('PyQt6')
    qtcore = types.ModuleType('PyQt6.QtCore')
    class _QObject:
        pass
    def _pyqtSignal(*args, **kwargs):
        class SignalStub:
            def __init__(self):
                self._callbacks = []
            def connect(self, cb):
                self._callbacks.append(cb)
            def emit(self, *a, **k):
                for cb in list(self._callbacks):
                    try:
                        cb(*a, **k)
                    except Exception:
                        pass
        return SignalStub()
    qtcore.QObject = _QObject
    qtcore.pyqtSignal = _pyqtSignal
    # Minimal QThread stub
    class _QThread:
        def __init__(self):
            self.started = _pyqtSignal()
            self.finished = _pyqtSignal()
        def start(self):
            try:
                self.started.emit()
            finally:
                try:
                    self.finished.emit()
                except Exception:
                    pass
        def quit(self):
            try:
                self.finished.emit()
            except Exception:
                pass
        def isRunning(self):
            return False

    def _pyqtSlot(*args, **kwargs):
        def _decorator(f):
            return f
        return _decorator

    qtcore.QThread = _QThread
    qtcore.pyqtSlot = _pyqtSlot
    pyqt6.QtCore = qtcore
    sys.modules['PyQt6'] = pyqt6
    sys.modules['PyQt6.QtCore'] = qtcore

import core.twitch_emotes as te


class DummyResponse:
    def __init__(self, status_code=200, data=None, text=''):
        self.status_code = status_code
        self._data = data or {'data': []}
        self.text = text
        self.content = b'PNGDATA'
        self.headers = {'Content-Type': 'image/png'}

    def json(self):
        return self._data


class TestTwitchPrefetch(unittest.TestCase):
    def setUp(self):
        # Create a fresh manager instance for each test
        self.manager = te.TwitchEmoteManager(config=None)
        # Replace network session with a mock
        self.manager.session = Mock()

    def test_prefetch_global_sync_sets_flag(self):
        sample = {'data': [{'id': '123', 'name': 'Kappa', 'images': {'url_1x': 'https://example.com/kappa.png'}}]}
        self.manager.session.get.return_value = DummyResponse(200, data=sample, text=str(sample))
        # Run synchronously to avoid background timing issues in test
        self.manager.prefetch_global(background=False)
        self.assertTrue(self.manager._warmed_global)
        self.assertIn('123', self.manager.id_map)
        self.assertIn('Kappa', self.manager.name_map)

    def test_prefetch_channel_sync_sets_channel_warmed(self):
        sample = {'data': [{'id': '456', 'name': 'PogChamp', 'images': {'url_1x': 'https://example.com/pog.png'}, 'emote_set_id': 'set1'}]}

        def side_effect(url, headers=None, params=None, timeout=None):
            # Return the same sample for both channel list and emote set endpoints
            return DummyResponse(200, data=sample, text=str(sample))

        self.manager.session.get.side_effect = side_effect
        self.manager.prefetch_channel('999', background=False)
        self.assertIn('999', getattr(self.manager, '_warmed_channels'))
        self.assertIn('456', self.manager.id_map)
        self.assertIn('PogChamp', self.manager.name_map)


if __name__ == '__main__':
    unittest.main()
