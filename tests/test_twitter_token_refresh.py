import importlib
from unittest.mock import Mock


def make_response(status=200, data=None, text=''):
    class Resp:
        def __init__(self, status, data, text):
            self.status_code = status
            self._data = data or {}
            self.text = text

        def json(self):
            return self._data

    return Resp(status, data, text)


def test_twitter_refresh_persists_refresh_token(monkeypatch):
    mod = importlib.import_module('platform_connectors.twitter_connector')
    TwitterConnector = mod.TwitterConnector

    cfg = Mock()
    cfg.get_platform_config.return_value = {'client_id': 'cid', 'client_secret': 'csec'}
    cfg.set_platform_config = Mock()

    conn = TwitterConnector(config=cfg)
    conn.refresh_token = 'r1'

    fake_resp = make_response(200, {'access_token': 'tok', 'refresh_token': 'newr'})

    class FakeSession:
        def post(self, *args, **kwargs):
            return fake_resp

    # Twitter connector tries make_retry_session() if available else requests.Session()
    monkeypatch.setattr(mod, 'make_retry_session', lambda: FakeSession())

    ok = conn.refresh_access_token()
    assert ok is True
    cfg.set_platform_config.assert_any_call('twitter', 'refresh_token', 'newr')


def test_twitter_refresh_failure_returns_false(monkeypatch):
    mod = importlib.import_module('platform_connectors.twitter_connector')
    TwitterConnector = mod.TwitterConnector

    cfg = Mock()
    cfg.get_platform_config.return_value = {'client_id': 'cid', 'client_secret': 'csec'}
    cfg.set_platform_config = Mock()

    conn = TwitterConnector(config=cfg)
    conn.refresh_token = 'r1'

    fake_resp = make_response(400, {}, 'bad')

    class FakeSession:
        def post(self, *args, **kwargs):
            return fake_resp

    monkeypatch.setattr(mod, 'make_retry_session', lambda: FakeSession())

    ok = conn.refresh_access_token()
    assert ok is False
    cfg.set_platform_config.assert_not_called()
