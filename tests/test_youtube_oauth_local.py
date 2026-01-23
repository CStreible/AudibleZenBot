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


def test_exchange_code_returns_token(monkeypatch):
    mod = importlib.import_module('platform_connectors.youtube_oauth_local')

    fake_resp = make_response(200, {'access_token': 'a', 'refresh_token': 'r'})

    class FakeSession:
        def post(self, *args, **kwargs):
            return fake_resp

    monkeypatch.setattr(mod, 'make_retry_session', lambda: FakeSession())

    result = mod.exchange_code_for_token('code')
    assert result == {'access_token': 'a', 'refresh_token': 'r'}


def test_exchange_code_handles_network_error(monkeypatch):
    mod = importlib.import_module('platform_connectors.youtube_oauth_local')

    class FakeSession:
        def post(self, *args, **kwargs):
            raise Exception('network')

    monkeypatch.setattr(mod, 'make_retry_session', lambda: FakeSession())

    result = mod.exchange_code_for_token('code')
    assert result is None
