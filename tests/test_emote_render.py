import unittest
import sys
import types
from unittest.mock import Mock

# Stub core.http_session.make_retry_session to avoid network in manager init
if 'core.http_session' not in sys.modules:
    mod = types.ModuleType('core.http_session')
    def _make_retry_session():
        return Mock()
    mod.make_retry_session = _make_retry_session
    sys.modules['core.http_session'] = mod

# Stub PyQt6.QtCore if not present (tests don't rely on real Qt)
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


class DummyTwitchManager:
    def __init__(self):
        self.id_map = {}
        self.name_map = {}
        self.session = Mock()

    def get_emote_data_uri(self, emote_id, broadcaster_id=None):
        # Return a predictable data URI for tests when id known
        if str(emote_id) in self.id_map or emote_id in self.id_map:
            return 'data:image/png;base64,AAA'
        return None

    def get_emote_data_uri_by_name(self, name, broadcaster_id=None):
        # If name present in name_map, return a data uri
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


class TestEmoteRender(unittest.TestCase):
    def setUp(self):
        # Inject stub managers
        import core.twitch_emotes as te
        import core.bttv_ffz as bf
        self._real_get_t = getattr(te, 'get_manager')
        self._real_get_b = getattr(bf, 'get_manager')
        te.get_manager = lambda cfg=None: self._tmgr
        bf.get_manager = lambda: self._bmgr

    def tearDown(self):
        import core.twitch_emotes as te
        import core.bttv_ffz as bf
        te.get_manager = self._real_get_t
        bf.get_manager = self._real_get_b

    def test_global_id_position_replacement(self):
        # Numeric emote id provided via emotes tag
        self._tmgr = DummyTwitchManager()
        self._bmgr = DummyBTTV()
        # register id in id_map so get_emote_data_uri returns data uri
        self._tmgr.id_map['123'] = {'name': 'Kappa'}

        html_out, has_img = emotes.render_message('Kappa', {'123': ['0-4']}, metadata=None)
        self.assertTrue(has_img)
        self.assertIn('data:image/png;base64,AAA', html_out)

    def test_name_based_replacement(self):
        self._tmgr = DummyTwitchManager()
        self._bmgr = DummyBTTV()
        # name-based lookup via get_emote_data_uri_by_name
        self._tmgr.name_map['PogChamp'] = '456'

        html_out, has_img = emotes.render_message('PogChamp', None, metadata={'room-id': '999'})
        self.assertTrue(has_img)
        self.assertIn('data:image/png;base64,BBB', html_out)

    def test_unknown_emote_no_replacement(self):
        self._tmgr = DummyTwitchManager()
        self._bmgr = DummyBTTV()

        html_out, has_img = emotes.render_message('NotAnEmote', None, metadata=None)
        self.assertFalse(has_img)
        self.assertIn('NotAnEmote', html_out)

    def test_emotesv2_token_resolution(self):
        self._tmgr = DummyTwitchManager()
        self._bmgr = DummyBTTV()
        # Emotesv2 token present in id_map
        token = 'emotesv2_abcdef'
        self._tmgr.id_map[token] = {'name': 'EV2'}

        # provide emotes_tag with positional range for the token (positions 4-19)
        msg = 'pre ' + token + ' post'
        # calculate positions: token starts at index 4
        html_out, has_img = emotes.render_message(msg, {token: [f'4-{4+len(token)-1}']}, metadata={'room-id': '777'})
        self.assertTrue(has_img)
        self.assertIn('data:image/png;base64,AAA', html_out)


if __name__ == '__main__':
    unittest.main()
