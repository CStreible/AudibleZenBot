import importlib
from unittest.mock import Mock, patch


def make_response(status=200, data=None, text=''):
    class Resp:
        def __init__(self, status, data, text):
            self.status_code = status
            self._data = data or {}
            self.text = text

        def json(self):
            return self._data

    return Resp(status, data, text)


def test_twitch_refresh_persists_streamer(monkeypatch):
    mod = importlib.import_module('platform_connectors.twitch_connector')
    TwitchConnector = mod.TwitchConnector

    # Mock config to capture set_platform_config calls
    cfg = Mock()
    cfg.get_platform_config.return_value = {'client_id': 'cid', 'client_secret': 'csec'}
    cfg.set_platform_config = Mock()

    # Ensure singleton is reset for test isolation
    TwitchConnector._streamer_instance = None
    conn = TwitchConnector(config=cfg, is_bot_account=False)
    conn.refresh_token = 'r1'

    fake_resp = make_response(200, {'access_token': 'newtok', 'refresh_token': 'newr'})

    class FakeSession:
        def mount(self, *a, **k):
            return None

        def post(self, *args, **kwargs):
            return fake_resp

    monkeypatch.setattr(mod.requests, 'Session', lambda: FakeSession())

    ok = conn.refresh_access_token()
    assert ok is True
    cfg.set_platform_config.assert_any_call('twitch', 'oauth_token', 'newtok')
    cfg.set_platform_config.assert_any_call('twitch', 'streamer_refresh_token', 'newr')


def test_twitch_refresh_persists_bot(monkeypatch):
    mod = importlib.import_module('platform_connectors.twitch_connector')
    TwitchConnector = mod.TwitchConnector

    cfg = Mock()
    cfg.get_platform_config.return_value = {'client_id': 'cid', 'client_secret': 'csec'}
    cfg.set_platform_config = Mock()

    # Reset singleton to avoid reusing streamer instance
    TwitchConnector._streamer_instance = None
    conn = TwitchConnector(config=cfg, is_bot_account=True)
    conn.refresh_token = 'r1'

    fake_resp = make_response(200, {'access_token': 'bottok', 'refresh_token': 'botr'})

    class FakeSession:
        def mount(self, *a, **k):
            return None

        def post(self, *args, **kwargs):
            return fake_resp

    monkeypatch.setattr(mod.requests, 'Session', lambda: FakeSession())

    ok = conn.refresh_access_token()
    assert ok is True
    cfg.set_platform_config.assert_any_call('twitch', 'bot_token', 'bottok')
    cfg.set_platform_config.assert_any_call('twitch', 'bot_refresh_token', 'botr')


def test_twitch_refresh_network_error(monkeypatch):
    mod = importlib.import_module('platform_connectors.twitch_connector')
    TwitchConnector = mod.TwitchConnector

    cfg = Mock()
    cfg.get_platform_config.return_value = {'client_id': 'cid', 'client_secret': 'csec'}
    cfg.set_platform_config = Mock()

    # Reset singleton to avoid reuse of previously-initialized instance
    TwitchConnector._streamer_instance = None
    conn = TwitchConnector(config=cfg)
    conn.refresh_token = 'r1'

    class FakeSession:
        def mount(self, *a, **k):
            return None

        def post(self, *args, **kwargs):
            raise mod.requests.exceptions.RequestException("network")

    monkeypatch.setattr(mod.requests, 'Session', lambda: FakeSession())

    ok = conn.refresh_access_token()
    # Network error -> None
    assert ok is None
    cfg.set_platform_config.assert_not_called()
