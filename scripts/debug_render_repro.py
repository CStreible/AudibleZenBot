import sys, types
from unittest.mock import Mock

# ensure core.http_session stub as tests do
if 'core.http_session' not in sys.modules:
    mod = types.ModuleType('core.http_session')
    def _make_retry_session():
        return Mock()
    mod.make_retry_session = _make_retry_session
    sys.modules['core.http_session'] = mod

# patch PyQt6 stub as tests
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

import core.emotes as emotes
import core.twitch_emotes as te
import core.bttv_ffz as bf

# Define Dummy managers same as tests
class DummyTwitchManager:
    def __init__(self):
        self.id_map = {}
        self.name_map = {}
        self.session = Mock()
    def get_emote_data_uri(self, emote_id, broadcaster_id=None):
        if str(emote_id) in self.id_map or emote_id in self.id_map:
            return 'data:image/png;base64,AAA'
        return None
    def get_emote_data_uri_by_name(self, name, broadcaster_id=None):
        if name in self.name_map:
            return 'data:image/png;base64,BBB'
        return None
    def get_emote_id_by_name(self, name, broadcaster_id=None):
        return self.name_map.get(name)
    def fetch_global_emotes(self):
        return None
    def fetch_channel_emotes(self, bid):
        return None

class DummyBTTV:
    def __init__(self):
        self.name_map = {}
    def ensure_channel(self, broadcaster_id):
        return None
    def get_emote_data_uri_by_name(self, name, broadcaster_id=None):
        return None

# Setup managers and patch get_manager
_tmgr = DummyTwitchManager()
_bmgr = DummyBTTV()
_tmgr.name_map['PogChamp'] = '456'

te.get_manager = lambda cfg=None: _tmgr
bf.get_manager = lambda: _bmgr

html_out, has_img = emotes.render_message('PogChamp', None, metadata={'room-id':'999'})
print('RESULT has_img=', has_img)
print('HTML:', html_out)

