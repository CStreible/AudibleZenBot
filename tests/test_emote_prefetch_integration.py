import unittest
import sys
import types
from unittest.mock import Mock
import threading

# Stub core.http_session.make_retry_session to avoid real network
if 'core.http_session' not in sys.modules:
    mod = types.ModuleType('core.http_session')
    def _make_retry_session():
        return Mock()
    mod.make_retry_session = _make_retry_session
    sys.modules['core.http_session'] = mod

# Stub PyQt6.QtCore if not present
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
from core.signals import signals as emote_signals


class DummyResponse:
    def __init__(self, status_code=200, data=None, text=''):
        self.status_code = status_code
        self._data = data or {'data': []}
        self.text = text
        self.content = b'PNG'
        self.headers = {'Content-Type': 'image/png'}

    def json(self):
        return self._data


class TestPrefetchIntegration(unittest.TestCase):
    def setUp(self):
        # fresh manager
        self.mgr = te.TwitchEmoteManager(config=None)
        # stub session
        self.mgr.session = Mock()

    def test_prefetch_global_emits_signal_and_sets_flag(self):
        called = {'sig': False}

        def on_global():
            called['sig'] = True

        # connect signal
        emote_signals.emotes_global_warmed.connect(on_global)

        # session.get returns a valid global emote payload
        sample = {'data': [{'id': 'g1', 'name': 'G1'}]}
        self.mgr.session.get.return_value = DummyResponse(200, data=sample, text=str(sample))

        t = self.mgr.prefetch_global(background=True)
        # join thread if it's a threading.Thread
        if isinstance(t, threading.Thread):
            t.join(timeout=1.0)

        self.assertTrue(self.mgr._warmed_global)
        self.assertTrue(called['sig'])

    def test_prefetch_channel_emits_signal_and_sets_channel_warmed(self):
        called = {'sig_bid': None}

        def on_channel(bid):
            called['sig_bid'] = bid

        emote_signals.emotes_channel_warmed.connect(on_channel)

        sample = {'data': [{'id': 'c1', 'name': 'C1', 'emote_set_id': 'set1'}]}

        def side_effect(url, headers=None, params=None, timeout=None):
            return DummyResponse(200, data=sample, text=str(sample))

        self.mgr.session.get.side_effect = side_effect

        t = self.mgr.prefetch_channel('42', background=True)
        if isinstance(t, threading.Thread):
            t.join(timeout=1.0)

        self.assertIn('42', getattr(self.mgr, '_warmed_channels'))
        # signal should have been called with broadcaster id
        self.assertEqual(called['sig_bid'], '42')


if __name__ == '__main__':
    unittest.main()
